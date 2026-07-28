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
            workflow_svc = WorkflowExecutionService(db)
            BATCH_SIZE = 100
            processed_count = 0
            offset = 0
            while True:
                emails = db.query(Email).offset(offset).limit(BATCH_SIZE).all()
                if not emails:
                    break
                for email in emails:
                    workflow_svc.process_email(email)
                    processed_count += 1
                db.commit()
                offset += BATCH_SIZE
                if len(emails) < BATCH_SIZE:
                    break
            logger.info(f"[SCHEDULER_JOB] Evaluated {processed_count} email(s) against active workflows.")
            log_scheduler_event("info", f"Evaluated {processed_count} email(s) against active workflows", {"processed": processed_count})
        except Exception as wf_err:
            logger.error(f"[SCHEDULER_JOB] Failed retroactive workflow execution: {wf_err}")
            log_scheduler_event("error", f"Retroactive workflow execution failed: {str(wf_err)}")
            db.rollback()

    except Exception as e:
        logger.error(f"[SCHEDULER_JOB] Exception in poll_mailboxes_job: {e}")
        log_scheduler_event("error", f"Exception in poll_mailboxes_job: {str(e)}")
    finally:
        db.close()
        logger.info("[SCHEDULER_JOB] Scheduled incremental mailbox poll completed.")
