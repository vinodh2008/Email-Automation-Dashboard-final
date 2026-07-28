"""
System Monitoring API Router.
Exposes comprehensive live monitoring metrics for APScheduler, database health, Gmail API, and mailbox status.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, desc
from app.db.session import get_db
from app.models import MailboxAccount, SyncRun, Email, SyncError
from app.scheduler.scheduler_service import scheduler_service
from app.config import settings
from app.auth.dependencies import get_current_user
import os

router = APIRouter(prefix="/system", tags=["System Monitoring"], dependencies=[Depends(get_current_user)])


@router.get("/status")
def get_system_status(db: Session = Depends(get_db)):
    """
    Returns single source of truth system monitoring status metrics.
    Consumed by Dashboard, Settings, Monitoring, and Operations views.
    """
    # 1. Scheduler Metrics
    sched_info = scheduler_service.get_status()

    # 2. Database Connection Check
    db_connected = False
    try:
        db.execute(text("SELECT 1")).scalar()
        db_connected = True
    except Exception:
        db_connected = False

    # 3. Mailbox Status
    mailbox = db.query(MailboxAccount).filter(MailboxAccount.sync_status != "disabled").order_by(desc(MailboxAccount.created_at)).first()
    
    current_gmail = mailbox.account_identifier if mailbox else "Not Connected"
    sync_status = mailbox.sync_status if mailbox else "disconnected"
    last_history_id = mailbox.last_history_id if mailbox else "N/A"
    last_sync_at = mailbox.last_sync_at.isoformat() if mailbox and mailbox.last_sync_at else None

    # 4. Sync Runs History
    last_successful_run = db.query(SyncRun).filter(SyncRun.status == "completed").order_by(desc(SyncRun.started_at)).first()
    last_failed_run = db.query(SyncRun).filter(SyncRun.status.in_(["failed", "partial_failure"])).order_by(desc(SyncRun.started_at)).first()

    total_emails = db.query(Email).count()
    total_sync_runs = db.query(SyncRun).count()
    recent_errors_count = db.query(SyncError).count()

    # 5. OAuth Credentials Check
    oauth_file_exists = os.path.exists(settings.google_token_file)
    oauth_status = "valid" if oauth_file_exists and mailbox and mailbox.sync_status == "connected" else "reauth_required"

    # 6. Overall Health Score Calculation
    health_score = 100.0
    if not db_connected:
        health_score = 0.0
    elif not sched_info["is_running"]:
        health_score -= 20.0
    if oauth_status != "valid":
        health_score -= 30.0
    if recent_errors_count > 10:
        health_score -= 15.0

    return {
        "scheduler": {
            "is_running": sched_info["is_running"],
            "health_state": sched_info["health_state"],
            "interval_minutes": sched_info["sync_interval_minutes"],
            "last_run_at": sched_info["last_run_at"],
            "next_run_at": sched_info["next_run_at"],
            "execution_count": sched_info["execution_count"],
            "failure_count": sched_info["failure_count"],
            "last_duration_seconds": sched_info["last_run_duration_seconds"]
        },
        "mailbox": {
            "current_gmail": current_gmail,
            "sync_status": sync_status,
            "last_history_id": last_history_id,
            "last_sync_at": last_sync_at,
            "oauth_status": oauth_status
        },
        "database": {
            "connected": db_connected,
            "total_emails": total_emails,
            "total_sync_runs": total_sync_runs,
            "recent_errors_count": recent_errors_count
        },
        "sync_history": {
            "last_successful_sync": last_successful_run.completed_at.isoformat() if last_successful_run and last_successful_run.completed_at else None,
            "last_failed_sync": last_failed_run.started_at.isoformat() if last_failed_run else None
        },
        "health_score": max(0.0, round(health_score, 1))
    }
