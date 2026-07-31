from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import DashboardSummaryResponse, RecentActivityResponse
from app.core.responses import success_response, APIResponse
from fastapi import Request
from app.auth.dependencies import get_current_user
from app.models.email import Email

router = APIRouter(prefix="/dashboard", tags=["Dashboard Foundation"], dependencies=[Depends(get_current_user)])

def get_dashboard_service(db: Session = Depends(get_db)) -> DashboardService:
    return DashboardService(db)

@router.get("/summary", response_model=APIResponse[DashboardSummaryResponse], summary="Get Dashboard Summary KPIs")
def get_summary(request: Request, service: DashboardService = Depends(get_dashboard_service)):
    """Returns aggregated metrics from the Gmail Collection Layer and Workflow executions."""
    return success_response(data=service.get_summary(), request_id=request.state.request_id)

@router.get("/recent-activity", response_model=APIResponse[RecentActivityResponse], summary="Get Recent Activity Feed")
def get_recent_activity(request: Request, service: DashboardService = Depends(get_dashboard_service)):
    """Returns a unified timeline of recent system events, errors, and workflow executions."""
    return success_response(data=service.get_recent_activity(), request_id=request.state.request_id)


@router.get("/metrics")
def get_automation_metrics(request: Request, db: Session = Depends(get_db)):
    """Returns Phase 2B automation metrics: auto-approval rate, queue depth, response time, success rate."""
    try:
        from app.models.ai_approval import AIApproval
        from app.models.task_queue import TaskQueue
        from sqlalchemy import func
        from datetime import datetime, timezone, timedelta

        total_emails = db.query(Email).count()

        auto_approved = db.query(AIApproval).filter(AIApproval.auto_approved == True).count()
        total_approvals = db.query(AIApproval).count()
        auto_approve_rate = round((auto_approved / total_approvals) * 100, 1) if total_approvals > 0 else 0.0

        queue_depth = db.query(TaskQueue).filter(TaskQueue.status == "pending").count()
        processing = db.query(TaskQueue).filter(TaskQueue.status == "processing").count()

        completed = db.query(TaskQueue).filter(TaskQueue.status == "completed").all()
        failed = db.query(TaskQueue).filter(TaskQueue.status.in_(["failed", "dead_letter"])).count()

        avg_response_ms = 0
        if completed:
            times = []
            for t in completed:
                if t.started_at and t.completed_at:
                    delta = (t.completed_at - t.started_at).total_seconds() * 1000
                    times.append(delta)
            if times:
                avg_response_ms = round(sum(times) / len(times), 0)

        total_tasks = len(completed) + failed
        success_rate = round((len(completed) / total_tasks) * 100, 1) if total_tasks > 0 else 100.0

        emails_sent = db.query(Email).filter(Email.ai_draft_status == "sent").count()

        return success_response(data={
            "total_emails": total_emails,
            "auto_approve_rate": auto_approve_rate,
            "total_approvals": total_approvals,
            "auto_approved_count": auto_approved,
            "queue_depth": queue_depth,
            "processing": processing,
            "avg_response_time_ms": avg_response_ms,
            "success_rate": success_rate,
            "total_tasks_completed": len(completed),
            "total_tasks_failed": failed,
            "emails_sent": emails_sent,
        })
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))
