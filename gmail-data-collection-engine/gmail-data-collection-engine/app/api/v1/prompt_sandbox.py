from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.services.prompt_sandbox_service import PromptSandboxService
from app.core.responses import success_response

router = APIRouter(prefix="/prompt-sandbox", tags=["prompt-sandbox"], dependencies=[Depends(get_current_user)])


class SandboxTestRequest(BaseModel):
    template_id: Optional[str] = None
    template_version: Optional[int] = None
    variable_values: dict = {}


class ValidateRequest(BaseModel):
    prompt_content: str
    variable_values: dict = {}


@router.post("/test")
def run_sandbox_test(payload: SandboxTestRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = PromptSandboxService(db)
    try:
        result = service.run_test(
            template_id=payload.template_id,
            variable_values=payload.variable_values,
            template_version=payload.template_version,
            user_id=current_user.get("id"),
        )
        return success_response(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate")
def validate_variables(payload: ValidateRequest, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = PromptSandboxService(db)
    result = service.validate_only(payload.prompt_content, payload.variable_values)
    return success_response(data=result)


@router.get("/history")
def get_history(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = PromptSandboxService(db)
    history = service.get_history(user_id=current_user.get("id"))
    return success_response(data=history)


@router.get("/history/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = PromptSandboxService(db)
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return success_response(data=session)
