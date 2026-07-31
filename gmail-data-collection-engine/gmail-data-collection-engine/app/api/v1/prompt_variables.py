from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import List, Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.services.prompt_variable_service import PromptVariableService
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/prompt-variables", tags=["prompt-variables"], dependencies=[Depends(get_current_user)])


class PromptVariableCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    data_type: Optional[str] = 'STRING'
    scope: Optional[str] = 'GLOBAL'
    source_adapter: Optional[str] = 'STATIC'
    source_config: Optional[dict] = None
    default_value: Optional[str] = None
    is_required: Optional[bool] = False
    validation_regex: Optional[str] = None
    sample_value: Optional[str] = None
    category: Optional[str] = 'email'

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        import re
        if not v or not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('Name must be lowercase letters, numbers, underscores, starting with a letter')
        return v


class PromptVariableUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    data_type: Optional[str] = None
    scope: Optional[str] = None
    source_adapter: Optional[str] = None
    source_config: Optional[dict] = None
    default_value: Optional[str] = None
    is_required: Optional[bool] = None
    validation_regex: Optional[str] = None
    sample_value: Optional[str] = None
    category: Optional[str] = None


@router.get("/")
def list_variables(scope: str = None, adapter: str = None, category: str = None, db: Session = Depends(get_db)):
    service = PromptVariableService(db)
    variables = service.list_variables(scope=scope, adapter=adapter, category=category)
    return success_response(data=[_to_response(v) for v in variables])


@router.get("/registry")
def get_registry(db: Session = Depends(get_db)):
    service = PromptVariableService(db)
    variables = service.get_registry()
    return success_response(data=[_to_response(v) for v in variables])


@router.get("/adapters")
def get_adapters(db: Session = Depends(get_db)):
    service = PromptVariableService(db)
    return success_response(data=service.get_adapters())


@router.post("/")
def create_variable(payload: PromptVariableCreate, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = PromptVariableService(db)
    try:
        data = payload.model_dump()
        variable = service.create_variable(data, user_id=current_user.get("id"))
        audit = AdminAuditService(db)
        audit.log(
            action="create", entity_type="prompt_variable", entity_id=str(variable.id),
            new_value={"name": variable.name, "display_name": variable.display_name},
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(data=_to_response(variable))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{variable_id}")
def update_variable(variable_id: str, payload: PromptVariableUpdate, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = PromptVariableService(db)
    try:
        data = payload.model_dump(exclude_unset=True)
        variable = service.update_variable(variable_id, data, user_id=current_user.get("id"))
        if not variable:
            raise HTTPException(status_code=404, detail="Variable not found")
        audit = AdminAuditService(db)
        audit.log(
            action="update", entity_type="prompt_variable", entity_id=variable_id,
            new_value={"name": variable.name},
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(data=_to_response(variable))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{variable_id}")
def delete_variable(variable_id: str, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = PromptVariableService(db)
    if not service.delete_variable(variable_id):
        raise HTTPException(status_code=404, detail="Variable not found")
    audit = AdminAuditService(db)
    audit.log(
        action="delete", entity_type="prompt_variable", entity_id=variable_id,
        user_id=current_user.get("id"), user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return success_response(message="Variable deleted")


def _to_response(v):
    return {
        'id': str(v.id),
        'name': v.name,
        'display_name': v.display_name,
        'description': v.description,
        'data_type': v.data_type,
        'scope': v.scope,
        'source_adapter': v.source_adapter,
        'source_config': v.source_config,
        'default_value': v.default_value,
        'is_required': v.is_required,
        'validation_regex': v.validation_regex,
        'sample_value': v.sample_value,
        'category': v.category,
        'is_active': v.is_active,
        'created_at': v.created_at.isoformat() if v.created_at else None,
        'updated_at': v.updated_at.isoformat() if v.updated_at else None,
    }
