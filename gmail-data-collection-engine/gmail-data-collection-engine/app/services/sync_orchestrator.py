"""
SyncOrchestrator — Centralized synchronization engine.

Handles the full lifecycle of email sync:
1. Atomic lock acquisition with TTL
2. Gmail API data retrieval (full or incremental)
3. Email parsing and database persistence
4. Attachment extraction, security filtering, and Supabase Storage upload
5. Comprehensive metrics tracking and error logging
6. Unconditional lock release
"""
import logging
import traceback
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from googleapiclient.errors import HttpError
from app.config import settings
from app.models.mailbox_account import MailboxAccount
from app.services.sync_service import SyncService
from app.services.email_service import EmailService
from app.services.attachment_service import AttachmentService
from app.services.workflow_execution_service import WorkflowExecutionService
from app.utils.gmail_parser import parse_gmail_message
from app.clients.supabase_client import get_supabase_client, ensure_bucket_exists, upload_attachment_with_retry
from app.utils.attachment_utils import extract_attachments, is_safe_file_type, generate_storage_path, decode_base64url

logger = logging.getLogger("sync_orchestrator")


class SyncOrchestrator:
    def __init__(self, db: Session, provider):
        self.db = db
        self.provider = provider
        self.sync_service = SyncService(db)
        self.email_service = EmailService(db)
        self.attachment_service = AttachmentService(db)
        self.workflow_execution_service = WorkflowExecutionService(db)
        
        self.supabase_client = get_supabase_client()
        ensure_bucket_exists(self.supabase_client, settings.supabase_storage_bucket)

    def run_sync(self, account_id: str, mode: str = "incremental") -> bool:
        """
        Execute a full sync lifecycle for the given mailbox account.
        Returns True if the sync executed (regardless of individual email failures).
        Returns False if the lock could not be acquired.
        """
        lock_token = str(uuid.uuid4())
        ttl_minutes = settings.sync_lock_ttl_minutes
        
        # --- Step 1: Atomic Lock Acquisition ---
        lock_query = text(f"""
            UPDATE mailbox_accounts 
            SET sync_status = 'syncing', 
                sync_lock_token = :token, 
                sync_locked_at = NOW(), 
                sync_lock_expires_at = NOW() + INTERVAL '{ttl_minutes} minutes'
            WHERE id = :id 
              AND (sync_status IN ('connected', 'idle', 'active') OR sync_lock_expires_at < NOW())
        """)
        
        res = self.db.execute(lock_query, {"token": lock_token, "id": account_id})
        self.db.commit()
        
        if res.rowcount == 0:
            logger.info(f"[LOCK] Mailbox {account_id} skipped — already locked or disabled.")
            return False
            
        logger.info(f"[LOCK] Lock acquired for mailbox {account_id} (token={lock_token[:8]}...)")
        
        try:
            account = self.db.query(MailboxAccount).filter(MailboxAccount.id == account_id).first()
            if not account:
                logger.error(f"[SYNC] Account {account_id} not found in database.")
                return False
                
            sync_cursor_before = account.last_history_id
            
            # --- Step 2: Fetch Gmail profile for latest historyId ---
            try:
                profile = self.provider.get_account_profile()
                history_id = str(profile.get("historyId"))
                logger.info(f"[SYNC] Gmail profile fetched. Current historyId: {history_id}")
            except Exception as e:
                logger.error(f"[SYNC] Failed to fetch Gmail profile: {str(e)}")
                return False

            sync_cursor_after = history_id
            account_identifier = str(account.account_identifier)

            fallback_full_sync_used = False
            history_pages_processed = 0
            incremental_message_ids_found = 0

            if mode == "incremental" and not sync_cursor_before:
                logger.info("[SYNC] No prior historyId. Bootstrapping with full sync.")
                mode = "full"

            # --- Step 3: Create sync run record ---
            run = self.sync_service.start_sync_run(account_id, sync_type=mode)
            run_id = str(run.id)
            logger.info(f"[SYNC] Sync run created: {run_id} (mode={mode})")
            
            # --- Metrics accumulators ---
            emails_found = 0
            emails_inserted = 0
            duplicates_skipped = 0
            emails_failed = 0
            emails_not_found = 0
            
            attachments_found = 0
            attachments_inserted = 0
            attachments_skipped = 0
            attachments_failed = 0
            status = "running"
            
            try:
                # --- Step 4: Fetch message IDs ---
                max_emails = settings.max_emails_per_sync
                msg_ids_to_process = []
                
                if mode == "incremental":
                    try:
                        logger.info(f"[SYNC] Fetching incremental changes since historyId={sync_cursor_before}")
                        msg_ids_list, new_history_id, history_pages_processed = self.provider.fetch_incremental_message_ids(sync_cursor_before)
                        sync_cursor_after = new_history_id
                        incremental_message_ids_found = len(msg_ids_list)
                        msg_ids_to_process = msg_ids_list[:max_emails] if max_emails else msg_ids_list
                        logger.info(f"[SYNC] Incremental: {incremental_message_ids_found} new message IDs found, {history_pages_processed} history pages processed.")
                        
                        # --- Safety Catch-Up Check for Downtime Gaps ---
                        if len(msg_ids_to_process) == 0 and account.last_sync_at:
                            downtime_seconds = (datetime.now(timezone.utc) - account.last_sync_at).total_seconds()
                            if downtime_seconds > 300: # Over 5 minutes of downtime/gap
                                epoch_ts = int(account.last_sync_at.timestamp())
                                logger.info(f"[SYNC] Downtime gap detected ({round(downtime_seconds)}s). Running reconciliation query 'after:{epoch_ts}'...")
                                query_ids = list(self.provider.fetch_message_ids(query=f"after:{epoch_ts}", max_results=max_emails))
                                if query_ids:
                                    logger.info(f"[SYNC] Reconciliation query recovered {len(query_ids)} message ID(s) missed during downtime.")
                                    msg_ids_to_process = query_ids
                    except HttpError as e:
                        if e.resp.status == 404:
                            logger.warning("[SYNC] HistoryId expired (404). Falling back to full sync.")
                            fallback_full_sync_used = True
                            mode = "full"
                        else:
                            raise e
                            
                if mode == "full":
                    logger.info(f"[SYNC] Running full sync (max={max_emails})")
                    msg_ids_to_process = list(self.provider.fetch_message_ids(max_results=max_emails))
                    sync_cursor_after = history_id
                    
                logger.info(f"[SYNC] Processing {len(msg_ids_to_process)} messages...")

                # --- Step 5: Process each message ---
                for msg_id in msg_ids_to_process:
                    emails_found += 1
                    try:
                        raw_detail = self.provider.fetch_message_detail(msg_id)
                        parsed_data = parse_gmail_message(raw_detail)
                        
                        inserted, email_obj = self.email_service.save_email(account_id, parsed_data)
                        
                        if inserted:
                            emails_inserted += 1
                            logger.debug(f"[EMAIL] Inserted: {msg_id} — {parsed_data.get('subject', '(no subject)')}")
                            
                            # --- Step 6: Process attachments ---
                            if parsed_data.get("has_attachments"):
                                extracted_atts = extract_attachments(parsed_data["raw_email_json"])
                                for att_meta in extracted_atts:
                                    attachments_found += 1
                                    if attachments_inserted >= settings.max_attachments_per_sync:
                                        attachments_skipped += 1
                                        continue
                                    
                                    provider_att_id = att_meta["provider_attachment_id"]
                                    filename = att_meta["filename"]
                                    size_bytes = att_meta["size"]
                                    
                                    if not is_safe_file_type(filename):
                                        logger.info(f"[ATTACHMENT] Skipping unsafe type: {filename}")
                                        attachments_skipped += 1
                                        continue
                                        
                                    if size_bytes > (settings.max_attachment_size_mb * 1024 * 1024):
                                        logger.info(f"[ATTACHMENT] Skipping oversized: {filename} ({size_bytes} bytes)")
                                        attachments_skipped += 1
                                        continue
                                    
                                    if self.attachment_service.attachment_exists(str(email_obj.id), provider_att_id):
                                        attachments_skipped += 1
                                        continue
                                    
                                    try:
                                        raw_att = self.provider.fetch_attachment(msg_id, provider_att_id)
                                        att_data_b64 = raw_att.get("data")
                                        if not att_data_b64:
                                            raise ValueError("No base64 data returned from provider.")
                                            
                                        file_bytes = decode_base64url(att_data_b64)
                                        storage_path = generate_storage_path(account_id, msg_id, provider_att_id, filename)
                                        
                                        uploaded_path = upload_attachment_with_retry(
                                            client=self.supabase_client,
                                            bucket_name=settings.supabase_storage_bucket,
                                            storage_path=storage_path,
                                            file_bytes=file_bytes,
                                            mime_type=att_meta["mime_type"]
                                        )
                                        
                                        saved_att = self.attachment_service.save_attachment(
                                            email_id=str(email_obj.id),
                                            provider_attachment_id=provider_att_id,
                                            filename=filename,
                                            mime_type=att_meta["mime_type"],
                                            size=size_bytes,
                                            storage_bucket=settings.supabase_storage_bucket,
                                            storage_path=uploaded_path
                                        )
                                        
                                        if saved_att:
                                            attachments_inserted += 1
                                            logger.debug(f"[ATTACHMENT] Uploaded: {filename}")
                                        else:
                                            attachments_skipped += 1
                                            
                                        self.db.commit()
                                    except Exception as att_err:
                                        self.db.rollback()
                                        attachments_failed += 1
                                        logger.warning(f"[ATTACHMENT] Failed: {filename} for email {msg_id}: {str(att_err)}")
                                        try:
                                            self.sync_service.log_sync_error(
                                                sync_run_id=run_id,
                                                gmail_message_id=msg_id,
                                                error_type=f"AttachmentError:{type(att_err).__name__}",
                                                error_message=str(att_err),
                                                error_stack=traceback.format_exc(),
                                                mailbox_account_id=account_id,
                                                api_endpoint="attachments.get"
                                            )
                                        except Exception as sync_e:
                                            try:
                                                self.db.rollback()
                                            except Exception:
                                                pass
                                            logger.error(f"[ERROR] Failed to log attachment error: {sync_e}")
                        else:
                            duplicates_skipped += 1
                            logger.debug(f"[EMAIL] Duplicate skipped: {msg_id}")
                            
                        self.db.commit()
                        
                        # --- Step 6.5: Enqueue Email for Async Processing ---
                        if inserted:
                            try:
                                from app.services.task_queue_service import TaskQueueService
                                task_queue = TaskQueueService(self.db)
                                task_queue.enqueue(
                                    queue_name="email_processing",
                                    task_type="classify",
                                    entity_type="email",
                                    entity_id=str(email_obj.id),
                                    payload={
                                        "email_id": str(email_obj.id),
                                        "account_id": account_id,
                                        "mailbox_account_id": account_id,
                                    },
                                    priority=5,
                                )
                                logger.info(f"[TASK_QUEUE] Enqueued email {msg_id} for async classification")
                            except Exception as tq_err:
                                logger.error(f"[TASK_QUEUE] Failed to enqueue email {msg_id}: {tq_err}")
                    except HttpError as e:
                        if e.resp.status == 404:
                            self.db.rollback()
                            emails_not_found += 1
                            logger.info(f"Gmail message {msg_id} not found (likely deleted). Skipping.")
                            try:
                                self.sync_service.log_sync_error(
                                    sync_run_id=run_id,
                                    gmail_message_id=msg_id,
                                    error_type="HttpError:404",
                                    error_message="Message not found",
                                    error_stack=traceback.format_exc(),
                                    mailbox_account_id=account_id,
                                    api_endpoint="messages.get"
                                )
                            except Exception as sync_err:
                                self.db.rollback()
                                logger.error(f"[ERROR] Failed to log sync error for msg {msg_id}: {sync_err}")
                            continue
                        else:
                            self.db.rollback()
                            emails_failed += 1
                            logger.warning(f"Failed to fetch Gmail message: {msg_id}")
                            try:
                                self.sync_service.log_sync_error(
                                    sync_run_id=run_id,
                                    gmail_message_id=msg_id,
                                    error_type=type(e).__name__,
                                    error_message=str(e),
                                    error_stack=traceback.format_exc(),
                                    mailbox_account_id=account_id,
                                    api_endpoint="messages.get"
                                )
                            except Exception as sync_err:
                                self.db.rollback()
                                logger.error(f"[ERROR] Failed to log sync error for msg {msg_id}: {sync_err}")
                    except Exception as e:
                        self.db.rollback()
                        emails_failed += 1
                        error_stack = traceback.format_exc()
                        logger.warning(f"Failed to fetch Gmail message: {msg_id}")
                        try:
                            self.sync_service.log_sync_error(
                                sync_run_id=run_id,
                                gmail_message_id=msg_id,
                                error_type=type(e).__name__,
                                error_message=str(e),
                                error_stack=error_stack,
                                mailbox_account_id=account_id,
                                api_endpoint="messages.get"
                            )
                        except Exception as sync_err:
                            self.db.rollback()
                            logger.error(f"[ERROR] Failed to log sync error for msg {msg_id}: {sync_err}")

                # --- Step 7: Determine final status ---
                # A 404 is not a system failure, it just means the email was deleted.
                # If all emails we tried were either successfully inserted, duplicated, or simply 404'd, the batch is considered successful and we MUST advance the cursor.
                valid_processed = emails_inserted + duplicates_skipped + emails_not_found
                
                if emails_failed > 0 and emails_failed == emails_found and emails_found > 0:
                    status = "failed"
                elif emails_failed > 0 or attachments_failed > 0:
                    status = "partial_failure"
                    # We still advance the cursor on partial failure so we don't get deadlocked
                    account.last_history_id = sync_cursor_after
                    account.last_sync_at = datetime.now(timezone.utc)
                    account.sync_status = "connected"
                    self.db.commit()
                else:
                    status = "completed"
                    account.last_history_id = sync_cursor_after
                    account.last_sync_at = datetime.now(timezone.utc)
                    account.sync_status = "connected"
                    self.db.commit()
                    
            except KeyboardInterrupt:
                self.db.rollback()
                logger.warning("[SYNC] Cancelled by user (KeyboardInterrupt).")
                status = "cancelled"
                
                from app.db.session import SessionLocal
                with SessionLocal() as fresh_db:
                    try:
                        fresh_sync_service = SyncService(fresh_db)
                        fresh_sync_service.log_sync_error(
                            sync_run_id=run_id,
                            gmail_message_id="N/A",
                            error_type="KeyboardInterrupt",
                            error_message="Sync manually cancelled by user.",
                            error_stack=traceback.format_exc(),
                            mailbox_account_id=account_id,
                            api_endpoint="sync_loop"
                        )
                        
                        fresh_sync_service.complete_sync_run(
                            sync_run_id=run_id,
                            status=status,
                            emails_found=emails_found,
                            emails_inserted=emails_inserted,
                            duplicates_skipped=duplicates_skipped,
                            emails_failed=emails_failed,
                            attachments_found=attachments_found,
                            attachments_inserted=attachments_inserted,
                            attachments_skipped=attachments_skipped,
                            attachments_failed=attachments_failed,
                            sync_cursor_before=sync_cursor_before,
                            sync_cursor_after=sync_cursor_after,
                            history_pages_processed=history_pages_processed,
                            incremental_message_ids_found=incremental_message_ids_found,
                            fallback_full_sync_used=fallback_full_sync_used
                        )
                    except Exception as e:
                        logger.error(f"[ERROR] Failed to record cancellation: {e}")
                        
                raise
                
            except Exception as e:
                self.db.rollback()
                logger.error(f"[SYNC] Fatal error during sync loop: {str(e)}")
                status = "failed"
                emails_failed = emails_found - (emails_inserted + duplicates_skipped)

            finally:
                # --- Step 8: Persist metrics ---
                if status != "cancelled":
                    try:
                        # Ensure clean transaction state before saving metrics
                        # Note: emails are already committed individually during the sync loop
                        try:
                            self.db.rollback()
                        except Exception:
                            pass
                        self.sync_service.complete_sync_run(
                            sync_run_id=run_id,
                            status=status,
                            emails_found=emails_found,
                            emails_inserted=emails_inserted,
                            duplicates_skipped=duplicates_skipped,
                            emails_failed=emails_failed,
                            attachments_found=attachments_found,
                            attachments_inserted=attachments_inserted,
                            attachments_skipped=attachments_skipped,
                            attachments_failed=attachments_failed,
                            sync_cursor_before=sync_cursor_before,
                            sync_cursor_after=sync_cursor_after,
                            history_pages_processed=history_pages_processed,
                            incremental_message_ids_found=incremental_message_ids_found,
                            fallback_full_sync_used=fallback_full_sync_used
                        )
                    except Exception as comp_e:
                        logger.error(f"[ERROR] Failed to complete sync run: {comp_e}")

            # --- Step 9: Log summary ---
            logger.info("=" * 60)
            logger.info("SYNC SUMMARY")
            logger.info("=" * 60)
            logger.info(f"  Sync Run ID        : {run_id}")
            logger.info(f"  Mailbox Account    : {account_identifier}")
            logger.info(f"  Sync Mode          : {mode}")
            logger.info(f"  Final Status       : {status}")
            logger.info(f"  ---")
            logger.info(f"  Emails Found       : {emails_found}")
            logger.info(f"  Emails Inserted    : {emails_inserted}")
            logger.info(f"  Duplicates Skipped : {duplicates_skipped}")
            logger.info(f"  Emails Failed      : {emails_failed}")
            logger.info(f"  Emails Processed   : {emails_inserted + duplicates_skipped}")
            logger.info(f"  ---")
            logger.info(f"  Attachments Found  : {attachments_found}")
            logger.info(f"  Attachments Uploaded: {attachments_inserted}")
            logger.info(f"  Attachments Skipped: {attachments_skipped}")
            logger.info(f"  Attachments Failed : {attachments_failed}")
            logger.info(f"  ---")
            logger.info(f"  History Cursor     : {sync_cursor_before} → {sync_cursor_after}")
            logger.info(f"  Fallback Full Sync : {fallback_full_sync_used}")
            logger.info("=" * 60)

            # --- Broadcast Real-Time SSE Event ---
            try:
                from app.api.v1.events import broadcast_event
                broadcast_event("sync_completed", {
                    "account_id": account_id,
                    "emails_inserted": emails_inserted,
                    "status": status,
                    "mode": mode
                })
            except Exception as sse_err:
                logger.warning(f"[SSE] Non-fatal error broadcasting sync event: {sse_err}")

            # --- Metrics validation ---
            expected_processed = emails_inserted + duplicates_skipped
            expected_total = emails_inserted + duplicates_skipped + emails_failed
            if expected_total != emails_found and emails_found > 0:
                logger.warning(
                    f"[METRICS] Consistency check: emails_found ({emails_found}) != "
                    f"inserted ({emails_inserted}) + skipped ({duplicates_skipped}) + failed ({emails_failed}) = {expected_total}"
                )
            else:
                logger.info("[METRICS] Metrics consistency check passed ✓")
                
            return True

        finally:
            # --- Step 10: Unconditional lock release ---
            unlock_query = text("""
                UPDATE mailbox_accounts 
                SET sync_status = 'connected', 
                    sync_lock_token = NULL,
                    sync_locked_at = NULL,
                    sync_lock_expires_at = NULL
                WHERE id = :id AND sync_lock_token = :token
            """)
            self.db.execute(unlock_query, {"id": account_id, "token": lock_token})
            self.db.commit()
            logger.info(f"[LOCK] Lock released for mailbox {account_id}")
