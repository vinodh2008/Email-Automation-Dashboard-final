from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.services.ai_defaults_service import AIDefaultsService
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/ai-defaults", tags=["ai-defaults"], dependencies=[Depends(get_current_user)])

VALID_TONES = {'professional', 'friendly', 'formal', 'casual', 'empathetic', 'direct', 'technical'}
VALID_LENGTHS = {'concise', 'medium', 'detailed', 'comprehensive'}


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

    @field_validator('default_tone')
    @classmethod
    def validate_tone(cls, v):
        if v is not None and v not in VALID_TONES:
            raise ValueError(f'Invalid tone. Must be one of: {", ".join(sorted(VALID_TONES))}')
        return v

    @field_validator('creativity_level')
    @classmethod
    def validate_creativity(cls, v):
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError('Creativity level must be between 0.0 and 1.0')
        return v

    @field_validator('response_length')
    @classmethod
    def validate_length(cls, v):
        if v is not None and v not in VALID_LENGTHS:
            raise ValueError(f'Invalid response length. Must be one of: {", ".join(sorted(VALID_LENGTHS))}')
        return v

    @field_validator('max_retry_count')
    @classmethod
    def validate_retry(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('Max retry count must be between 0 and 10')
        return v

    @field_validator('max_tokens')
    @classmethod
    def validate_tokens(cls, v):
        if v is not None and (v < 100 or v > 128000):
            raise ValueError('Max tokens must be between 100 and 128000')
        return v


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
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return success_response(data=new_data)
