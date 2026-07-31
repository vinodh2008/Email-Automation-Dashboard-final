from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.services.category_workflow_mapping_service import CategoryWorkflowMappingService
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/category-workflow-mappings", tags=["category-workflow-mappings"], dependencies=[Depends(get_current_user)])


class MappingCreate(BaseModel):
    business_category_id: str
    workflow_id: str
    priority: Optional[int] = 0
    is_active: Optional[bool] = True


class MappingUpdate(BaseModel):
    priority: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/")
def list_mappings(category_id: str = None, workflow_id: str = None, db: Session = Depends(get_db)):
    service = CategoryWorkflowMappingService(db)
    mappings = service.list_mappings(category_id=category_id, workflow_id=workflow_id)
    return success_response(data=[_to_response(m) for m in mappings])


@router.post("/")
def create_mapping(payload: MappingCreate, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = CategoryWorkflowMappingService(db)
    try:
        data = payload.model_dump()
        mapping = service.create_mapping(data, user_id=current_user.get("id"))
        audit = AdminAuditService(db)
        audit.log(
            action="create", entity_type="category_workflow_mapping", entity_id=str(mapping.id),
            new_value={"category_id": mapping.business_category_id, "workflow_id": mapping.workflow_id},
            user_id=current_user.get("id"), user_email=current_user.get("email"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.commit()
        return success_response(data=_to_response(mapping))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{mapping_id}")
def update_mapping(mapping_id: str, payload: MappingUpdate, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = CategoryWorkflowMappingService(db)
    mapping = service.update_mapping(mapping_id, payload.model_dump(exclude_unset=True), user_id=current_user.get("id"))
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    audit = AdminAuditService(db)
    audit.log(
        action="update", entity_type="category_workflow_mapping", entity_id=mapping_id,
        new_value={"priority": mapping.priority, "is_active": mapping.is_active},
        user_id=current_user.get("id"), user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return success_response(data=_to_response(mapping))


@router.delete("/{mapping_id}")
def delete_mapping(mapping_id: str, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = CategoryWorkflowMappingService(db)
    if not service.delete_mapping(mapping_id):
        raise HTTPException(status_code=404, detail="Mapping not found")
    audit = AdminAuditService(db)
    audit.log(
        action="delete", entity_type="category_workflow_mapping", entity_id=mapping_id,
        user_id=current_user.get("id"), user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return success_response(message="Mapping deleted")


def _to_response(m):
    return {
        'id': str(m.id),
        'business_category_id': str(m.business_category_id),
        'workflow_id': str(m.workflow_id),
        'priority': m.priority,
        'is_active': m.is_active,
        'created_at': m.created_at.isoformat() if m.created_at else None,
    }
