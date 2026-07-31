"""
Scheduler Job Definitions.
Contains execution logic for scheduled background tasks.
"""
import logging
from app.db.session import SessionLocal
from app.models.mailbox_account import MailboxAccount
from app.models.email import Email
from app.providers.gmail_provider import GmailProvider
from app.services.sync_orchestrator import SyncOrchestrator
from app.services.workflow_execution_service import WorkflowExecutionService
from app.services.system_logger import log_scheduler_event, log_sync_event

from app.auth.gmail_oauth import NonInteractiveAuthRequired

logger = logging.getLogger("scheduler_jobs")

ALLOWED_SYNC_STATUSES = {"connected", "idle", "syncing"}


def poll_mailboxes_job():
    """
    Background job triggered by APScheduler.
    Executes incremental Gmail synchronization only for mailboxes that are:
      - is_active = True
      - sync_status IN ('connected', 'idle', 'syncing')
    Never polls: disconnected, oauth_failed, disabled, error.
    """
    logger.info("[SCHEDULER_JOB] Starting scheduled incremental mailbox poll...")
    log_scheduler_event("info", "Starting scheduled incremental mailbox poll")
    db = SessionLocal()
    try:
        mailboxes = db.query(MailboxAccount).filter(
            MailboxAccount.is_active == True,
            MailboxAccount.sync_status.in_(ALLOWED_SYNC_STATUSES)
        ).all()
        logger.info(f"[SCHEDULER_JOB] Found {len(mailboxes)} eligible mailbox account(s) for polling.")
        log_scheduler_event("info", f"Found {len(mailboxes)} eligible mailbox(es)", {"count": len(mailboxes)})

        for account in mailboxes:
            provider = GmailProvider()
            try:
                provider.authenticate(interactive=False)
                orchestrator = SyncOrchestrator(db, provider)
                orchestrator.run_sync(str(account.id), mode="incremental")
                log_sync_event("info", f"Sync completed for {account.account_identifier}", mailbox_id=str(account.id))
            except NonInteractiveAuthRequired:
                logger.warning(f"[SCHEDULER_JOB] Mailbox {account.id} requires re-auth. Setting status to 'oauth_failed'.")
                log_sync_event("warning", f"Mailbox requires re-auth: {account.account_identifier}", mailbox_id=str(account.id))
                account.sync_status = 'oauth_failed'
                db.commit()
            except Exception as e:
                logger.error(f"[SCHEDULER_JOB] Failed to sync mailbox {account.id}: {e}")
                log_sync_event("error", f"Sync failed for {account.account_identifier}: {str(e)}", mailbox_id=str(account.id))

        try:
            log_scheduler_event("info", "Retroactive workflow execution disabled — using async task queue")
        except Exception as wf_err:
            pass

    except Exception as e:
        logger.error(f"[SCHEDULER_JOB] Exception in poll_mailboxes_job: {e}")
        log_scheduler_event("error", f"Exception in poll_mailboxes_job: {str(e)}")
    finally:
        db.close()
        logger.info("[SCHEDULER_JOB] Scheduled incremental mailbox poll completed.")


def process_task_queue_job():
    """
    Background job to process pending tasks from the task queue.
    Runs every 5 seconds via APScheduler.
    """
    logger.info("[TASK_QUEUE_JOB] Processing task queue...")
    db = SessionLocal()
    try:
        from app.services.task_queue_service import TaskQueueService
        from app.services.category_matcher_service import CategoryMatcherService
        from app.services.ai_task_service import AITaskService
        from app.services.decision_service import DecisionService
        from app.services.validation_service import ValidationService
        from app.models.email import Email
        from app.models.business_category import BusinessCategory
        from app.models.ai_approval import AIApproval
        import uuid
        
        tq = TaskQueueService(db)
        tasks = tq.dequeue(limit=10)
        
        if not tasks:
            return
        
        logger.info(f"[TASK_QUEUE_JOB] Processing {len(tasks)} task(s)")
        
        for task in tasks:
            task_id = task["id"]
            task_type = task["task_type"]
            entity_id = task["entity_id"]
            payload = task.get("payload", {})
            
            try:
                if task_type == "classify":
                    # Step 1: Validate
                    validator = ValidationService(db)
                    validation = validator.validate(entity_id)
                    
                    if validation["score"] < 50:
                        logger.info(f"[TASK_QUEUE_JOB] Email {entity_id} rejected (score={validation['score']})")
                        tq.complete(task_id, {"validation": validation})
                        continue
                    
                    # Step 2: Classify
                    matcher = CategoryMatcherService(db)
                    classification = matcher.classify(entity_id)
                    
                    # Update email with classification
                    email = db.query(Email).filter(Email.id == entity_id).first()
                    if email and classification:
                        email.business_category_id = uuid.UUID(classification["category_id"])
                        email.classification_confidence = classification["confidence"]
                        db.commit()
                    
                    # Step 3: Enqueue AI tasks
                    if classification:
                        category_id = classification["category_id"]
                        ai_task_svc = AITaskService(db)
                        tasks_for_category = ai_task_svc.get_tasks_for_category(category_id)
                        
                        for ai_task in tasks_for_category:
                            tq.enqueue(
                                queue_name="ai_generation",
                                task_type="execute_ai_task",
                                entity_type="email",
                                entity_id=entity_id,
                                payload={
                                    "email_id": entity_id,
                                    "category_id": category_id,
                                    "ai_task_id": ai_task["id"],
                                    "task_type": ai_task["task_type"],
                                },
                                priority=5,
                            )
                    
                    tq.complete(task_id, {"classification": classification})
                    logger.info(f"[TASK_QUEUE_JOB] Email {entity_id} classified")
                
                elif task_type == "execute_ai_task":
                    # Execute AI task
                    ai_task_svc = AITaskService(db)
                    result = ai_task_svc.execute_task(
                        task_id=payload.get("ai_task_id"),
                        email_id=entity_id,
                        context=payload,
                    )
                    
                    if result and result.get("status") == "success":
                        # If this was a generate_reply task, create approval
                        if payload.get("task_type") == "generate_reply":
                            email = db.query(Email).filter(Email.id == entity_id).first()
                            if email:
                                # Decision
                                decision_svc = DecisionService(db)
                                decision = decision_svc.decide(
                                    email_id=entity_id,
                                    ai_output={
                                        "confidence": email.classification_confidence or 0.5,
                                        "risk_level": "low",
                                        "sender_email": email.sender_email or "",
                                    },
                                    category_id=payload.get("category_id"),
                                )
                                
                                approval = AIApproval(
                                    workflow_id=None,
                                    email_id=uuid.UUID(entity_id),
                                    generated_content=result.get("generated_content", ""),
                                    status="pending_review",
                                    auto_approved=decision.get("action") == "auto_approve",
                                    confidence_score=email.classification_confidence,
                                    decision_rule_id=uuid.UUID(decision["rule_id"]) if decision.get("rule_id") else None,
                                )
                                db.add(approval)
                                db.flush()
                                
                                email.ai_draft_status = "generated"
                                email.ai_draft_content = result.get("generated_content", "")
                                db.commit()
                                
                                if decision.get("action") == "auto_approve":
                                    tq.enqueue(
                                        queue_name="email_sending",
                                        task_type="send_email",
                                        entity_type="email",
                                        entity_id=entity_id,
                                        payload={
                                            "email_id": entity_id,
                                            "approval_id": str(approval.id),
                                        },
                                        priority=9,
                                    )
                                    logger.info(f"[TASK_QUEUE_JOB] Auto-approved email {entity_id}, enqueued for sending")
                    
                    tq.complete(task_id, result)
                    logger.info(f"[TASK_QUEUE_JOB] AI task completed for email {entity_id}")
                
                elif task_type == "send_email":
                    from app.services.email_sender_service import EmailSenderService
                    sender = EmailSenderService(db)
                    result = sender.send_reply(payload.get("approval_id", ""))
                    tq.complete(task_id, result)
                    logger.info(f"[TASK_QUEUE_JOB] Send result for email {entity_id}: {result.get('status')}")
                
                else:
                    tq.complete(task_id, {"status": "unknown_task_type"})
                    logger.warning(f"[TASK_QUEUE_JOB] Unknown task type: {task_type}")
                    
            except Exception as task_err:
                logger.error(f"[TASK_QUEUE_JOB] Task {task_id} failed: {task_err}")
                db.rollback()
                tq.fail(task_id, str(task_err))
    
    except Exception as e:
        logger.error(f"[TASK_QUEUE_JOB] Critical error: {e}")
    finally:
        db.close()
