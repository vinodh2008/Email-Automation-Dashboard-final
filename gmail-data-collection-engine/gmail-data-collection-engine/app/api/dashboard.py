"""
Dashboard API — Review and demo endpoints for project managers and reviewers.

Provides read-only views of system state without requiring direct database access.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.db.session import get_db
from app.models import MailboxAccount, Email, Attachment, SyncRun, SyncError
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])

@router.get("/metrics")
def dashboard_metrics(db: Session = Depends(get_db)):
    """Return aggregated metrics for frontend monitoring dashboard"""
    total_mailboxes = db.query(func.count(MailboxAccount.id)).scalar() or 0
    total_emails = db.query(func.count(Email.id)).scalar() or 0
    total_attachments = db.query(func.count(Attachment.id)).scalar() or 0
    total_sync_runs = db.query(func.count(SyncRun.id)).scalar() or 0
    total_sync_errors = db.query(func.count(SyncError.id)).scalar() or 0
    return [
        {"title": "Mailboxes", "val": str(total_mailboxes), "icon": "mail", "color": "bg-blue-100"},
        {"title": "Emails Collected", "val": str(total_emails), "icon": "inbox", "color": "bg-purple-100"},
        {"title": "Attachments", "val": str(total_attachments), "icon": "paperclip", "color": "bg-green-100"},
        {"title": "Sync Runs", "val": str(total_sync_runs), "icon": "repeat", "color": "bg-yellow-100"},
        {"title": "Sync Errors", "val": str(total_sync_errors), "icon": "alert-circle", "color": "bg-red-100"},
    ]


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    """High-level system summary with aggregate counts."""
    total_mailboxes = db.query(func.count(MailboxAccount.id)).scalar() or 0
    total_emails = db.query(func.count(Email.id)).scalar() or 0
    total_attachments = db.query(func.count(Attachment.id)).scalar() or 0
    total_sync_runs = db.query(func.count(SyncRun.id)).scalar() or 0
    total_sync_errors = db.query(func.count(SyncError.id)).scalar() or 0

    successful_syncs = db.query(func.count(SyncRun.id)).filter(
        SyncRun.status == "completed"
    ).scalar() or 0
    failed_syncs = db.query(func.count(SyncRun.id)).filter(
        SyncRun.status == "failed"
    ).scalar() or 0
    partial_syncs = db.query(func.count(SyncRun.id)).filter(
        SyncRun.status == "partial_failure"
    ).scalar() or 0

    total_inserted = db.query(func.coalesce(func.sum(SyncRun.emails_inserted), 0)).scalar()
    total_duplicates = db.query(func.coalesce(func.sum(SyncRun.duplicates_skipped), 0)).scalar()
    total_att_uploaded = db.query(func.coalesce(func.sum(SyncRun.attachments_uploaded), 0)).scalar()

    return {
        "project": "Utservio Gmail Communication Data Collection Engine",
        "version": "1.0.0",
        "sprint": "Sprint 2",
        "status": "Production Ready",
        "counts": {
            "mailbox_accounts": total_mailboxes,
            "emails_collected": total_emails,
            "attachments_stored": total_attachments,
            "sync_runs_total": total_sync_runs,
            "sync_errors_total": total_sync_errors,
        },
        "sync_stats": {
            "successful_syncs": successful_syncs,
            "failed_syncs": failed_syncs,
            "partial_failure_syncs": partial_syncs,
            "total_emails_inserted": total_inserted,
            "total_duplicates_prevented": total_duplicates,
            "total_attachments_uploaded": total_att_uploaded,
        },
    }


@router.get("/project-status")
def project_status():
    """Sprint 2 feature completion status for reviewers."""
    return {
        "project": "Utservio Gmail Communication Data Collection Engine",
        "sprint": "Sprint 2",
        "team": ["Vinodh", "Aakash"],
        "objective": "Build a reusable communication data collection engine for future AI-powered Email Automation Platform",
        "completed_phases": [
            {"phase": "Phase 1", "name": "Project Setup & Architecture", "status": "✅ Completed"},
            {"phase": "Phase 2", "name": "Gmail OAuth 2.0 Integration", "status": "✅ Completed"},
            {"phase": "Phase 3", "name": "Email Synchronization & Parsing", "status": "✅ Completed"},
            {"phase": "Phase 4", "name": "Incremental Sync & Duplicate Prevention", "status": "✅ Completed"},
            {"phase": "Phase 5", "name": "Attachment Processing & Storage", "status": "✅ Completed"},
            {"phase": "Phase 6A", "name": "SyncOrchestrator Centralization", "status": "✅ Completed"},
            {"phase": "Phase 6B", "name": "Automated Scheduler & Distributed Locking", "status": "✅ Completed"},
            {"phase": "Phase 7", "name": "Testing, Documentation & Finalization", "status": "✅ Completed"},
        ],
        "key_features": [
            "Gmail Desktop OAuth 2.0 (gmail.readonly scope)",
            "Full and incremental email synchronization",
            "MIME-recursive email body extraction",
            "Attachment security filtering and Supabase Storage upload",
            "Atomic distributed mailbox locking with TTL recovery",
            "APScheduler automated background synchronization",
            "Comprehensive sync_runs audit trail with metrics",
            "AI-readiness fields for future processing pipeline",
            "Row Level Security on all database tables",
        ],
        "technology_stack": {
            "backend": "Python 3.10+ / FastAPI",
            "database": "Supabase PostgreSQL",
            "storage": "Supabase Storage",
            "email_api": "Gmail API v1",
            "scheduler": "APScheduler (BlockingScheduler)",
            "orm": "SQLAlchemy 2.0",
            "testing": "pytest",
        },
    }


@router.get("/recent-emails")
def recent_emails(limit: int = 20, db: Session = Depends(get_db)):
    """List recently synced emails with key metadata (no raw JSON)."""
    emails = (
        db.query(Email)
        .order_by(Email.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return [
        {
            "id": str(e.id),
            "subject": e.subject,
            "sender": e.sender_email,
            "to": e.to_recipients,
            "received_at": str(e.received_at) if e.received_at else None,
            "labels": e.labels,
            "is_read": e.is_read,
            "has_attachments": e.has_attachments,
            "processing_status": e.processing_status,
            "ai_processing_status": e.ai_processing_status,
            "record_status": e.record_status,
            "created_at": str(e.created_at),
        }
        for e in emails
    ]


@router.get("/recent-syncs")
def recent_syncs(limit: int = 10, db: Session = Depends(get_db)):
    """List recent sync runs with full metrics."""
    runs = (
        db.query(SyncRun)
        .order_by(SyncRun.started_at.desc())
        .limit(min(limit, 50))
        .all()
    )
    return [
        {
            "id": str(r.id),
            "mailbox_account_id": str(r.mailbox_account_id),
            "sync_type": r.sync_type,
            "status": r.status,
            "started_at": str(r.started_at),
            "completed_at": str(r.completed_at) if r.completed_at else None,
            "duration_seconds": r.sync_duration_seconds,
            "metrics": {
                "emails_found": r.emails_found,
                "emails_processed": r.emails_processed,
                "emails_inserted": r.emails_inserted,
                "duplicates_skipped": r.duplicates_skipped,
                "emails_failed": r.emails_failed,
                "attachments_found": r.attachments_found,
                "attachments_uploaded": r.attachments_uploaded,
                "attachments_failed": r.attachments_failed,
            },
            "sync_cursor_before": r.sync_cursor_before,
            "sync_cursor_after": r.sync_cursor_after,
            "fallback_full_sync_used": r.fallback_full_sync_used,
            "history_pages_processed": r.history_pages_processed,
            "incremental_message_ids_found": r.incremental_message_ids_found,
            "error_summary": r.error_summary,
        }
        for r in runs
    ]


@router.get("/mailboxes")
def dashboard_mailboxes(db: Session = Depends(get_db)):
    """List all mailbox accounts with sync and lock status."""
    accounts = db.query(MailboxAccount).all()
    return [
        {
            "id": str(a.id),
            "provider": a.provider,
            "account_identifier": a.account_identifier,
            "auth_mode": a.auth_mode,
            "sync_status": a.sync_status,
            "last_history_id": a.last_history_id,
            "last_sync_at": str(a.last_sync_at) if a.last_sync_at else None,
            "lock": {
                "is_locked": a.sync_lock_token is not None,
                "locked_at": str(a.sync_locked_at) if a.sync_locked_at else None,
                "expires_at": str(a.sync_lock_expires_at) if a.sync_lock_expires_at else None,
            },
            "created_at": str(a.created_at),
        }
        for a in accounts
    ]


@router.get("/attachments")
def dashboard_attachments(limit: int = 20, db: Session = Depends(get_db)):
    """List recent attachments with storage metadata."""
    atts = (
        db.query(Attachment)
        .order_by(Attachment.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return [
        {
            "id": str(a.id),
            "email_id": str(a.email_id),
            "file_name": a.file_name,
            "mime_type": a.mime_type,
            "size_bytes": a.size_bytes,
            "storage_bucket": a.storage_bucket,
            "storage_path": a.storage_path,
            "download_status": a.download_status,
            "created_at": str(a.created_at),
        }
        for a in atts
    ]
