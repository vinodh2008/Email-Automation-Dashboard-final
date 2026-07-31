from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.services.ai_task_service import AITaskService
from app.core.responses import success_response

router = APIRouter(prefix="/categories", tags=["categories-pipeline"], dependencies=[Depends(get_current_user)])


@router.post("/{category_id}/execute-tasks")
def execute_category_tasks(
    category_id: str,
    email_id: str = Body(..., embed=True),
    knowledge_context: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    try:
        svc = AITaskService(db)
        results = svc.execute_task_chain(email_id, category_id)
        if not results:
            raise HTTPException(status_code=404, detail="No tasks found for category or execution failed")
        return success_response(data={
            "tasks_executed": len(results),
            "results": results,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{category_id}/knowledge/retrieve")
def retrieve_knowledge(
    category_id: str,
    query: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    try:
        from app.services.knowledge_service import KnowledgeService
        svc = KnowledgeService(db)
        results = svc.search_context(category_id, query)
        return success_response(data=results)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
