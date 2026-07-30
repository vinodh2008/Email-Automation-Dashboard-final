from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.services.company_settings_service import CompanySettingsService
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/company-settings", tags=["company-settings"], dependencies=[Depends(get_current_user)])


class CompanySettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    support_email: Optional[str] = None
    default_signature: Optional[str] = None
    default_language: Optional[str] = None
    timezone: Optional[str] = None
    business_hours: Optional[Dict[str, Any]] = None
    branding: Optional[Dict[str, Any]] = None


@router.get("/")
def get_company_settings(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = CompanySettingsService(db)
    data = service.get()
    return success_response(data=data)


@router.put("/")
def update_company_settings(
    payload: CompanySettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("update_users")),
):
    service = CompanySettingsService(db)
    old_data = service.get()
    new_data = service.update(payload.model_dump(exclude_unset=True), user_id=current_user.get("id"))
    audit = AdminAuditService(db)
    audit.log(
        action="update",
        entity_type="company_settings",
        entity_id="company_settings",
        old_value=old_data,
        new_value=new_data,
        user_id=current_user.get("id"),
        user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
    )
    return success_response(data=new_data)
