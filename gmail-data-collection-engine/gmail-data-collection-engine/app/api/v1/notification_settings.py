import logging
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.models.system_settings import SystemSetting
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

logger = logging.getLogger("notification_settings")

router = APIRouter(prefix="/notification-settings", tags=["notification-settings"], dependencies=[Depends(get_current_user)])


DEFAULT_NOTIFICATIONS = {
    "provider_failure_alerts": True,
    "sync_error_alerts": True,
    "approval_reminders": True,
    "daily_digest": False,
    "digest_email": "",
}


class NotificationSettingsUpdate(BaseModel):
    provider_failure_alerts: Optional[bool] = None
    sync_error_alerts: Optional[bool] = None
    approval_reminders: Optional[bool] = None
    daily_digest: Optional[bool] = None
    digest_email: Optional[str] = None


def _get_notifications(db: Session) -> dict:
    setting = db.query(SystemSetting).filter(SystemSetting.key == "notification_settings").first()
    if not setting:
        return dict(DEFAULT_NOTIFICATIONS)
    return dict(setting.value_json) if setting.value_json else dict(DEFAULT_NOTIFICATIONS)


@router.get("/")
def get_notification_settings(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    data = _get_notifications(db)
    return success_response(data=data)


@router.put("/")
def update_notification_settings(
    payload: NotificationSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("update_users")),
):
    setting = db.query(SystemSetting).filter(SystemSetting.key == "notification_settings").first()
    current = _get_notifications(db)
    merged = {**current, **{k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}}
    if setting:
        old_value = dict(setting.value_json)
        setting.value_json = merged
    else:
        old_value = None
        setting = SystemSetting(
            key="notification_settings",
            value_json=merged,
            description="System notification preferences",
            category="notifications",
            updated_by=current_user.get("id"),
        )
        db.add(setting)
    db.commit()
    db.refresh(setting)
    audit = AdminAuditService(db)
    audit.log(
        action="update",
        entity_type="notification_settings",
        entity_id="notification_settings",
        old_value=old_value,
        new_value=merged,
        user_id=current_user.get("id"),
        user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
    )
    return success_response(data=merged)
