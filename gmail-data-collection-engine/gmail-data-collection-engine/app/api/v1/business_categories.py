from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.services.business_category_service import BusinessCategoryService
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/business-categories", tags=["business-categories"], dependencies=[Depends(get_current_user)])


class BusinessCategoryCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    priority: Optional[int] = 0
    display_order: Optional[int] = 0
    color: Optional[str] = '#6366F1'
    icon: Optional[str] = None
    owner_user_id: Optional[str] = None
    status: Optional[str] = 'active'
    is_default: Optional[bool] = False
    ai_model: Optional[str] = None
    ai_temperature: Optional[float] = None
    ai_max_tokens: Optional[int] = None
    ai_timeout: Optional[int] = None
    ai_retry_count: Optional[int] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) < 1 or len(v) > 150:
            raise ValueError('Category name must be 1-150 characters')
        return v.strip()

    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        import re
        if not v or not re.match(r'^[A-Z][A-Z0-9_]*$', v):
            raise ValueError('Code must be uppercase letters, numbers, underscores, starting with a letter')
        return v


class BusinessCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    display_order: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    owner_user_id: Optional[str] = None
    status: Optional[str] = None
    is_default: Optional[bool] = None
    ai_model: Optional[str] = None
    ai_temperature: Optional[float] = None
    ai_max_tokens: Optional[int] = None
    ai_timeout: Optional[int] = None
    ai_retry_count: Optional[int] = None


class AIConfigUpdate(BaseModel):
    ai_model: Optional[str] = None
    ai_temperature: Optional[float] = None
    ai_max_tokens: Optional[int] = None
    ai_timeout: Optional[int] = None
    ai_retry_count: Optional[int] = None


@router.get("/")
def list_categories(db: Session = Depends(get_db)):
    service = BusinessCategoryService(db)
    categories = service.list_categories()
    result = []
    for c in categories:
        prompt_count = len(service.get_category_prompts(str(c.id)))
        workflow_count = len(service.get_category_workflows(str(c.id)))
        result.append(_to_response(c, prompt_count=prompt_count, workflow_count=workflow_count))
    return success_response(data=result)


@router.post("/")
def create_category(payload: BusinessCategoryCreate, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessCategoryService(db)
    try:
        data = payload.model_dump()
        category = service.create_category(data, user_id=current_user.get("id"))
        audit = AdminAuditService(db)
        audit.log(
            action="create", entity_type="business_category", entity_id=str(category.id),
            new_value={"name": category.name, "code": category.code},
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(data=_to_response(category))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{category_id}")
def get_category(category_id: str, db: Session = Depends(get_db)):
    service = BusinessCategoryService(db)
    category = service.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    prompt_count = len(service.get_category_prompts(category_id))
    workflow_count = len(service.get_category_workflows(category_id))
    metrics = service.get_category_metrics(category_id)
    return success_response(data=_to_response(category, prompt_count=prompt_count, workflow_count=workflow_count, metrics=metrics))


@router.put("/{category_id}")
def update_category(category_id: str, payload: BusinessCategoryUpdate, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessCategoryService(db)
    try:
        data = payload.model_dump(exclude_unset=True)
        category = service.update_category(category_id, data, user_id=current_user.get("id"))
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        audit = AdminAuditService(db)
        audit.log(
            action="update", entity_type="business_category", entity_id=category_id,
            new_value={"name": category.name, "code": category.code},
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(data=_to_response(category))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{category_id}")
def delete_category(category_id: str, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessCategoryService(db)
    try:
        if not service.delete_category(category_id):
            raise HTTPException(status_code=404, detail="Category not found")
        audit = AdminAuditService(db)
        audit.log(
            action="delete", entity_type="business_category", entity_id=category_id,
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(message="Category deleted")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{category_id}/set-default")
def set_default(category_id: str, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessCategoryService(db)
    if not service.set_default(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    audit = AdminAuditService(db)
    audit.log(
        action="set_default", entity_type="business_category", entity_id=category_id,
        user_id=current_user.get("id"), user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return success_response(message="Default category set")


@router.get("/{category_id}/prompts")
def get_category_prompts(category_id: str, db: Session = Depends(get_db)):
    service = BusinessCategoryService(db)
    prompts = service.get_category_prompts(category_id)
    return success_response(data=[{
        'id': str(p.id), 'name': p.name, 'status': p.status,
        'current_version': p.current_version, 'testing_status': p.testing_status,
    } for p in prompts])


@router.get("/{category_id}/workflows")
def get_category_workflows(category_id: str, db: Session = Depends(get_db)):
    service = BusinessCategoryService(db)
    mappings = service.get_category_workflows(category_id)
    return success_response(data=[{
        'id': str(m.id), 'workflow_id': str(m.workflow_id),
        'priority': m.priority, 'is_active': m.is_active,
    } for m in mappings])


@router.put("/{category_id}/ai-config")
def update_ai_config(category_id: str, payload: AIConfigUpdate, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessCategoryService(db)
    try:
        category = service.update_ai_config(category_id, payload.model_dump(exclude_unset=True), user_id=current_user.get("id"))
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        audit = AdminAuditService(db)
        audit.log(
            action="update_ai_config", entity_type="business_category", entity_id=category_id,
            new_value={"ai_model": category.ai_model, "ai_temperature": category.ai_temperature},
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(data=_to_response(category))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{category_id}/metrics")
def get_category_metrics(category_id: str, db: Session = Depends(get_db)):
    service = BusinessCategoryService(db)
    metrics = service.get_category_metrics(category_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Category not found")
    return success_response(data=metrics)


def _to_response(c, prompt_count=0, workflow_count=0, metrics=None):
    return {
        'id': str(c.id),
        'name': c.name,
        'code': c.code,
        'description': c.description,
        'priority': c.priority,
        'display_order': c.display_order,
        'color': c.color,
        'icon': c.icon,
        'owner_user_id': str(c.owner_user_id) if c.owner_user_id else None,
        'status': c.status,
        'default_prompt_template_id': str(c.default_prompt_template_id) if c.default_prompt_template_id else None,
        'default_workflow_id': str(c.default_workflow_id) if c.default_workflow_id else None,
        'is_default': c.is_default,
        'is_active': c.is_active,
        'prompt_count': prompt_count,
        'workflow_count': workflow_count,
        'ai_model': c.ai_model,
        'ai_temperature': c.ai_temperature,
        'ai_max_tokens': c.ai_max_tokens,
        'ai_timeout': c.ai_timeout,
        'ai_retry_count': c.ai_retry_count,
        'metrics': metrics or {},
        'created_at': c.created_at.isoformat() if c.created_at else None,
        'updated_at': c.updated_at.isoformat() if c.updated_at else None,
    }
