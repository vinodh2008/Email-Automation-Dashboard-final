from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.services.ai_task_service import AITaskService
from app.core.responses import success_response

router = APIRouter(prefix="/ai-tasks", tags=["ai-tasks"], dependencies=[Depends(get_current_user)])


class AITaskCreate(BaseModel):
    business_category_id: str
    task_type: str
    name: str
    description: Optional[str] = None
    prompt_template_id: Optional[str] = None
    model_override: Optional[str] = None
    temperature_override: Optional[float] = None
    max_tokens_override: Optional[int] = None
    execution_order: Optional[int] = 0
    config: Optional[dict] = {}


class AITaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prompt_template_id: Optional[str] = None
    model_override: Optional[str] = None
    temperature_override: Optional[float] = None
    max_tokens_override: Optional[int] = None
    is_enabled: Optional[bool] = None
    execution_order: Optional[int] = None
    config: Optional[dict] = None


@router.get("/")
def list_ai_tasks(category_id: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        svc = AITaskService(db)
        if category_id:
            tasks = svc.get_tasks_for_category(category_id)
        else:
            tasks = svc.get_tasks_for_category(category_id) if category_id else []
        return success_response(data=tasks)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/")
def create_ai_task(task_data: AITaskCreate, db: Session = Depends(get_db)):
    try:
        svc = AITaskService(db)
        result = svc.create_task(task_data.business_category_id, task_data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create task")
        return success_response(data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{task_id}")
def update_ai_task(task_id: str, task_data: AITaskUpdate, db: Session = Depends(get_db)):
    try:
        svc = AITaskService(db)
        result = svc.update_task(task_id, task_data.model_dump(exclude_unset=True))
        if not result:
            raise HTTPException(status_code=404, detail="Task not found")
        return success_response(data={"status": "updated"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}")
def delete_ai_task(task_id: str, db: Session = Depends(get_db)):
    try:
        svc = AITaskService(db)
        result = svc.delete_task(task_id)
        if not result:
            raise HTTPException(status_code=404, detail="Task not found")
        return success_response(data={"status": "deleted"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/test")
def test_ai_task(task_id: str, email_id: str, db: Session = Depends(get_db)):
    try:
        svc = AITaskService(db)
        result = svc.execute_task(task_id, email_id)
        if not result:
            raise HTTPException(status_code=404, detail="Task or email not found")
        return success_response(data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
