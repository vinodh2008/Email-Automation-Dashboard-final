"""
SyncService — Manages sync_runs and sync_errors lifecycle.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import SyncRun, SyncError
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, db: Session):
        self.db = db

    def start_sync_run(self, mailbox_account_id: str, sync_type: str) -> SyncRun:
        """Create a new sync run record with 'running' status."""
        run = SyncRun(
            mailbox_account_id=mailbox_account_id,
            sync_type=sync_type,
            status="running",
            emails_processed=0,
            emails_failed=0
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def log_sync_error(
        self,
        sync_run_id: str,
        gmail_message_id: str,
        error_type: str,
        error_message: str,
        error_stack: str = None,
        mailbox_account_id: str = None,
        api_endpoint: str = None
    ):
        """Log a granular error for a specific message or attachment within a sync run."""
        err = SyncError(
            sync_run_id=sync_run_id,
            gmail_message_id=gmail_message_id,
            mailbox_account_id=mailbox_account_id,
            api_endpoint=api_endpoint,
            error_type=error_type,
            error_message=error_message,
            error_stack=error_stack
        )
        self.db.add(err)
        self.db.commit()

    def complete_sync_run(
        self,
        sync_run_id: str,
        status: str,
        emails_found: int = 0,
        emails_inserted: int = 0,
        duplicates_skipped: int = 0,
        emails_failed: int = 0,
        attachments_found: int = 0,
        attachments_inserted: int = 0,
        attachments_skipped: int = 0,
        attachments_failed: int = 0,
        sync_cursor_before: str = None,
        sync_cursor_after: str = None,
        history_pages_processed: int = 0,
        incremental_message_ids_found: int = 0,
        fallback_full_sync_used: bool = False
    ):
        """Finalize a sync run with all accumulated metrics."""
        run = self.db.query(SyncRun).filter(SyncRun.id == sync_run_id).first()
        if not run:
            logger.error(f"SyncRun {sync_run_id} not found — cannot complete.")
            return

        run.status = status
        
        # --- Email metrics ---
        run.emails_found = emails_found
        run.emails_processed = emails_inserted + duplicates_skipped
        run.emails_inserted = emails_inserted
        run.duplicates_skipped = duplicates_skipped
        run.emails_failed = emails_failed
        
        # --- Attachment metrics ---
        run.attachments_found = attachments_found
        run.attachments_uploaded = attachments_inserted
        run.attachments_failed = attachments_failed
        
        # --- Error count ---
        run.error_count = emails_failed + attachments_failed
        
        # --- Sync cursors ---
        run.sync_cursor_before = sync_cursor_before
        run.sync_cursor_after = sync_cursor_after
        
        # --- Incremental tracking ---
        run.history_pages_processed = history_pages_processed
        run.incremental_message_ids_found = incremental_message_ids_found
        run.fallback_full_sync_used = fallback_full_sync_used
        
        # --- Timing ---
        run.completed_at = datetime.now(timezone.utc)
        self.db.flush()
        
        if run.completed_at and run.started_at:
            duration = run.completed_at - run.started_at
            run.sync_duration_seconds = int(duration.total_seconds())

        # --- Error summary ---
        if emails_failed > 0 or attachments_failed > 0:
            run.error_summary = f"{emails_failed} email(s) failed, {attachments_failed} attachment(s) failed"
            
        self.db.commit()
        
        logger.info(
            f"SyncRun {sync_run_id} completed: status={status}, "
            f"found={emails_found}, inserted={emails_inserted}, "
            f"duplicates={duplicates_skipped}, failed={emails_failed}"
        )
