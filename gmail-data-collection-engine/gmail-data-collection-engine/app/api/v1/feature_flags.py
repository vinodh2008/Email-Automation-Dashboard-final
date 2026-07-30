from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.services.feature_flags_service import FeatureFlagsService
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/feature-flags", tags=["feature-flags"], dependencies=[Depends(get_current_user)])


class FeatureFlagUpdate(BaseModel):
    flag_name: str
    enabled: bool


class FeatureFlagsBulkUpdate(BaseModel):
    flags: Dict[str, bool]


@router.get("/")
def get_feature_flags(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    service = FeatureFlagsService(db)
    data = service.get_all()
    return success_response(data=data)


@router.put("/")
def update_feature_flags(
    payload: FeatureFlagsBulkUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("update_users")),
):
    service = FeatureFlagsService(db)
    old_data = service.get_all()
    new_data = service.update_all(payload.flags, user_id=current_user.get("id"))
    audit = AdminAuditService(db)
    audit.log(
        action="update",
        entity_type="feature_flags",
        entity_id="feature_flags",
        old_value=old_data,
        new_value=new_data,
        user_id=current_user.get("id"),
        user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
    )
    return success_response(data=new_data)


@router.put("/toggle")
def toggle_feature_flag(
    payload: FeatureFlagUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("update_users")),
):
    service = FeatureFlagsService(db)
    old_data = service.get_all()
    new_data = service.update_flag(payload.flag_name, payload.enabled, user_id=current_user.get("id"))
    if not new_data:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Unknown feature flag: {payload.flag_name}")
    audit = AdminAuditService(db)
    audit.log(
        action="toggle",
        entity_type="feature_flag",
        entity_id=payload.flag_name,
        old_value={payload.flag_name: old_data.get(payload.flag_name, False)},
        new_value={payload.flag_name: payload.enabled},
        user_id=current_user.get("id"),
        user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
    )
    return success_response(data=new_data)
