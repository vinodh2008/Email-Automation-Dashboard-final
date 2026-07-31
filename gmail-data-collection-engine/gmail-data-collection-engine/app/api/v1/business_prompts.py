from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.services.business_prompt_service import BusinessPromptService
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/business-prompts", tags=["business-prompts"], dependencies=[Depends(get_current_user)])


class BusinessPromptCreate(BaseModel):
    business_category_id: Optional[str] = None
    name: str
    purpose: Optional[str] = None
    description: Optional[str] = None
    prompt_content: str
    variables_json: Optional[str] = '[]'


class BusinessPromptUpdate(BaseModel):
    name: Optional[str] = None
    purpose: Optional[str] = None
    description: Optional[str] = None
    prompt_content: Optional[str] = None
    variables_json: Optional[str] = None
    business_category_id: Optional[str] = None


class PublishRequest(BaseModel):
    change_summary: str


class RollbackRequest(BaseModel):
    target_version: int


@router.get("/")
def list_templates(category_id: str = None, status: str = None, db: Session = Depends(get_db)):
    service = BusinessPromptService(db)
    templates = service.list_templates(category_id=category_id, status=status)
    return success_response(data=[_to_response(t) for t in templates])


@router.post("/")
def create_template(payload: BusinessPromptCreate, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessPromptService(db)
    try:
        data = payload.model_dump()
        template = service.create_template(data, user_id=current_user.get("id"))
        audit = AdminAuditService(db)
        audit.log(
            action="create", entity_type="business_prompt", entity_id=str(template.id),
            new_value={"name": template.name, "category_id": template.business_category_id},
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(data=_to_response(template))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{template_id}")
def get_template(template_id: str, db: Session = Depends(get_db)):
    service = BusinessPromptService(db)
    template = service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    versions = service.get_versions(template_id)
    return success_response(data={
        **_to_response(template),
        'versions': [{
            'version_number': v.version_number,
            'status': v.status,
            'change_summary': v.change_summary,
            'published_at': v.published_at.isoformat() if v.published_at else None,
            'archived_at': v.archived_at.isoformat() if v.archived_at else None,
            'rollback_from_version': v.rollback_from_version,
            'created_by': str(v.created_by) if v.created_by else None,
            'created_at': v.created_at.isoformat() if v.created_at else None,
            'sandbox_result': v.sandbox_result,
        } for v in versions],
    })


@router.put("/{template_id}")
def update_template(template_id: str, payload: BusinessPromptUpdate, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessPromptService(db)
    try:
        data = payload.model_dump(exclude_unset=True)
        template = service.update_template(template_id, data, user_id=current_user.get("id"))
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        audit = AdminAuditService(db)
        audit.log(
            action="update", entity_type="business_prompt", entity_id=template_id,
            new_value={"name": template.name},
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(data=_to_response(template))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{template_id}")
def delete_template(template_id: str, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessPromptService(db)
    if not service.delete_template(template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    audit = AdminAuditService(db)
    audit.log(
        action="delete", entity_type="business_prompt", entity_id=template_id,
        user_id=current_user.get("id"), user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return success_response(message="Template deleted")


@router.post("/{template_id}/publish")
def publish_template(template_id: str, payload: PublishRequest, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessPromptService(db)
    try:
        result = service.publish_template(template_id, payload.change_summary, user_id=current_user.get("id"))
        if not result:
            raise HTTPException(status_code=404, detail="Template not found")
        audit = AdminAuditService(db)
        audit.log(
            action="publish", entity_type="business_prompt", entity_id=template_id,
            new_value={"version": result['version']},
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/rollback")
def rollback_template(template_id: str, payload: RollbackRequest, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessPromptService(db)
    try:
        result = service.rollback_template(template_id, payload.target_version, user_id=current_user.get("id"))
        if not result:
            raise HTTPException(status_code=404, detail="Template not found")
        audit = AdminAuditService(db)
        audit.log(
            action="rollback", entity_type="business_prompt", entity_id=template_id,
            new_value={"version": result['version'], "rollback_from": result['rollback_from']},
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/archive")
def archive_template(template_id: str, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessPromptService(db)
    try:
        result = service.archive_template(template_id, user_id=current_user.get("id"))
        if not result:
            raise HTTPException(status_code=404, detail="Template not found")
        audit = AdminAuditService(db)
        audit.log(
            action="archive", entity_type="business_prompt", entity_id=template_id,
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{template_id}/versions")
def get_versions(template_id: str, db: Session = Depends(get_db)):
    service = BusinessPromptService(db)
    versions = service.get_versions(template_id)
    return success_response(data=[{
        'version_number': v.version_number,
        'status': v.status,
        'change_summary': v.change_summary,
        'published_at': v.published_at.isoformat() if v.published_at else None,
        'archived_at': v.archived_at.isoformat() if v.archived_at else None,
        'rollback_from_version': v.rollback_from_version,
        'created_at': v.created_at.isoformat() if v.created_at else None,
    } for v in versions])


@router.get("/{template_id}/versions/{version_number}")
def get_version(template_id: str, version_number: int, db: Session = Depends(get_db)):
    service = BusinessPromptService(db)
    version = service.get_version(template_id, version_number)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return success_response(data={
        'version_number': version.version_number,
        'name': version.name,
        'prompt_content': version.prompt_content,
        'variables_json': version.variables_json,
        'status': version.status,
        'change_summary': version.change_summary,
        'sandbox_result': version.sandbox_result,
        'published_at': version.published_at.isoformat() if version.published_at else None,
        'archived_at': version.archived_at.isoformat() if version.archived_at else None,
        'rollback_from_version': version.rollback_from_version,
        'created_at': version.created_at.isoformat() if version.created_at else None,
    })


@router.post("/{template_id}/clone")
def clone_template(template_id: str, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = BusinessPromptService(db)
    clone = service.clone_template(template_id, user_id=current_user.get("id"))
    if not clone:
        raise HTTPException(status_code=404, detail="Template not found")
    audit = AdminAuditService(db)
    audit.log(
        action="clone", entity_type="business_prompt", entity_id=template_id,
        new_value={"clone_id": str(clone.id), "name": clone.name},
        user_id=current_user.get("id"), user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return success_response(data=_to_response(clone))


def _to_response(t):
    return {
        'id': str(t.id),
        'business_category_id': str(t.business_category_id) if t.business_category_id else None,
        'name': t.name,
        'purpose': t.purpose,
        'description': t.description,
        'prompt_content': t.prompt_content,
        'variables_json': t.variables_json,
        'current_version': t.current_version,
        'published_version': t.published_version,
        'testing_status': t.testing_status,
        'status': t.status,
        'usage_count': t.usage_count,
        'is_active': t.is_active,
        'created_at': t.created_at.isoformat() if t.created_at else None,
        'updated_at': t.updated_at.isoformat() if t.updated_at else None,
    }
