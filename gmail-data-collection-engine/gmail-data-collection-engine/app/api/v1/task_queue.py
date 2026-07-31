from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.services.task_queue_service import TaskQueueService
from app.core.responses import success_response

router = APIRouter(prefix="/task-queue", tags=["task-queue"], dependencies=[Depends(get_current_user)])


@router.get("/stats")
def get_queue_stats(db: Session = Depends(get_db)):
    try:
        svc = TaskQueueService(db)
        stats = svc.get_stats()
        return success_response(data=stats)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pending")
def get_pending_tasks(limit: int = 50, db: Session = Depends(get_db)):
    try:
        svc = TaskQueueService(db)
        tasks = svc.get_pending_tasks(limit=limit)
        return success_response(data=tasks)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retry/{task_id}")
def retry_task(task_id: str, db: Session = Depends(get_db)):
    try:
        svc = TaskQueueService(db)
        result = svc.retry(task_id)
        if not result:
            raise HTTPException(status_code=404, detail="Task not found or not retryable")
        return success_response(data={"status": "retried"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}")
def cancel_task(task_id: str, db: Session = Depends(get_db)):
    try:
        svc = TaskQueueService(db)
        result = svc.cancel(task_id)
        if not result:
            raise HTTPException(status_code=404, detail="Task not found or not cancellable")
        return success_response(data={"status": "cancelled"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
