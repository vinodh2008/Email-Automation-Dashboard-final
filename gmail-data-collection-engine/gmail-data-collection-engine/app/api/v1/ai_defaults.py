from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.services.ai_defaults_service import AIDefaultsService
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/ai-defaults", tags=["ai-defaults"], dependencies=[Depends(get_current_user)])


class AIDefaultsUpdate(BaseModel):
    default_tone: Optional[str] = None
    creativity_level: Optional[float] = None
    response_length: Optional[str] = None
    default_language: Optional[str] = None
    require_human_approval: Optional[bool] = None
    max_retry_count: Optional[int] = None
    max_tokens: Optional[int] = None
    default_model: Optional[str] = None
    fallback_enabled: Optional[bool] = None


@router.get("/")
def get_ai_defaults(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = AIDefaultsService(db)
    data = service.get()
    return success_response(data=data)


@router.put("/")
def update_ai_defaults(
    payload: AIDefaultsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("update_users")),
):
    service = AIDefaultsService(db)
    old_data = service.get()
    new_data = service.update(payload.model_dump(exclude_unset=True), user_id=current_user.get("id"))
    audit = AdminAuditService(db)
    audit.log(
        action="update",
        entity_type="ai_defaults",
        entity_id="ai_defaults",
        old_value=old_data,
        new_value=new_data,
        user_id=current_user.get("id"),
        user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
    )
    return success_response(data=new_data)
