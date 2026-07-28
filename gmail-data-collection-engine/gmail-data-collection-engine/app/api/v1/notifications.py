from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from datetime import datetime, timedelta, timezone
from app.db.session import get_db
from app.models import WorkflowExecution, SyncError, Email, SyncRun
from pydantic import BaseModel
from typing import List
from app.core.responses import success_response, APIResponse
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"], dependencies=[Depends(get_current_user)])

class NotificationItem(BaseModel):
    id: str
    type: str
    message: str
    timestamp: str

@router.get("", response_model=APIResponse[List[NotificationItem]])
def get_notifications(
    show_success: bool = Query(True, description="Toggle successful execution notifications"),
    db: Session = Depends(get_db)
):
    notifications = []
    now = datetime.now(timezone.utc)
    twenty_four_hours_ago = now - timedelta(hours=24)
    six_hours_ago = now - timedelta(hours=6)

    # 1. Failed workflow executions
    failed_execs = db.query(WorkflowExecution).options(
        joinedload(WorkflowExecution.workflow), 
        joinedload(WorkflowExecution.email)
    ).filter(
        WorkflowExecution.status == 'failed',
        WorkflowExecution.executed_at >= twenty_four_hours_ago
    ).all()
    
    for ex in failed_execs:
        workflow_name = ex.workflow.name if ex.workflow else 'Unknown Workflow'
        subject = ex.email.subject if ex.email else 'Unknown Email'
        notifications.append(NotificationItem(
            id=f"we_fail_{ex.id}",
            type="error",
            message=f"Workflow '{workflow_name}' failed on email '{subject}'",
            timestamp=ex.executed_at.isoformat()
        ))

    # 2. Successful workflow executions
    if show_success:
        success_execs = db.query(WorkflowExecution).options(
            joinedload(WorkflowExecution.workflow)
        ).filter(
            WorkflowExecution.status == 'success',
            WorkflowExecution.executed_at >= twenty_four_hours_ago
        ).all()
        
        for ex in success_execs:
            workflow_name = ex.workflow.name if ex.workflow else 'Unknown Workflow'
            notifications.append(NotificationItem(
                id=f"we_succ_{ex.id}",
                type="success",
                message=f"Workflow '{workflow_name}' matched a new email",
                timestamp=ex.executed_at.isoformat()
            ))

    # 3. Sync errors
    sync_errors = db.query(SyncError).filter(
        SyncError.created_at >= twenty_four_hours_ago
    ).all()
    for se in sync_errors:
        notifications.append(NotificationItem(
            id=f"se_{se.id}",
            type="error",
            message="Gmail sync failed — check connection",
            timestamp=se.created_at.isoformat()
        ))

    # 4. Uncategorized emails (last 6h)
    uncategorized_count = db.query(Email).filter(
        or_(Email.retention_category == None, Email.retention_category == 'Uncategorized'),
        Email.created_at >= six_hours_ago
    ).count()
    
    if uncategorized_count >= 5:
        notifications.append(NotificationItem(
            id=f"uncat_{int(now.timestamp())}",
            type="warning",
            message=f"{uncategorized_count} emails today didn't match any workflow — review Email Monitoring",
            timestamp=now.isoformat()
        ))

    # 5. Scheduler health (last successful sync > 5m ago)
    last_sync = db.query(SyncRun).filter(
        SyncRun.status == 'completed'
    ).order_by(SyncRun.started_at.desc()).first()

    if last_sync:
        time_since_sync = now - last_sync.started_at
        if time_since_sync > timedelta(minutes=5):
            mins_ago = int(time_since_sync.total_seconds() / 60)
            
            # Format elapsed time gracefully
            if mins_ago > 120:
                hours_ago = mins_ago // 60
                time_str = f"{hours_ago} hours"
            else:
                time_str = f"{mins_ago} minutes"
                
            notifications.append(NotificationItem(
                id=f"sched_fail_{int(now.timestamp())}",
                type="error",
                message=f"Scheduler appears stopped — last sync was {time_str} ago",
                timestamp=now.isoformat()
            ))
    else:
        # If no sync ever ran successfully
        notifications.append(NotificationItem(
            id=f"sched_fail_never_{int(now.timestamp())}",
            type="error",
            message=f"Scheduler has never completed a successful sync",
            timestamp=now.isoformat()
        ))

    # Sort descending by timestamp
    notifications.sort(key=lambda x: x.timestamp, reverse=True)
    
    # Return top 20
    return success_response(data=notifications[:20])
