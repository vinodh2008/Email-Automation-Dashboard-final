import re
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, List

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.services.company_settings_service import CompanySettingsService
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/company-settings", tags=["company-settings"], dependencies=[Depends(get_current_user)])

VALID_TIMEZONES = {
    'UTC', 'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
    'America/Sao_Paulo', 'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Asia/Tokyo',
    'Asia/Shanghai', 'Asia/Kolkata', 'Asia/Dubai', 'Australia/Sydney', 'Pacific/Auckland',
}
EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')
TIME_RE = re.compile(r'^([01]\d|2[0-3]):[0-5]\d$')


class CompanySettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    support_email: Optional[str] = None
    default_signature: Optional[str] = None
    default_language: Optional[str] = None
    timezone: Optional[str] = None
    business_hours: Optional[Dict[str, Any]] = None
    branding: Optional[Dict[str, Any]] = None

    @field_validator('company_name')
    @classmethod
    def validate_company_name(cls, v):
        if v is not None and (len(v) < 1 or len(v) > 200):
            raise ValueError('Company name must be 1-200 characters')
        return v

    @field_validator('support_email')
    @classmethod
    def validate_support_email(cls, v):
        if v is not None and v != '' and not EMAIL_RE.match(v):
            raise ValueError('Invalid email format')
        return v

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v):
        if v is not None and v not in VALID_TIMEZONES:
            raise ValueError(f'Invalid timezone. Must be one of: {", ".join(sorted(VALID_TIMEZONES))}')
        return v

    @field_validator('business_hours')
    @classmethod
    def validate_business_hours(cls, v):
        if v is None:
            return v
        valid_days = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'}
        for day, hours in v.items():
            if day.lower() not in valid_days:
                raise ValueError(f'Invalid day: {day}')
            if isinstance(hours, dict):
                if 'start' in hours and not TIME_RE.match(str(hours['start'])):
                    raise ValueError(f'Invalid start time for {day}: must be HH:MM (24h)')
                if 'end' in hours and not TIME_RE.match(str(hours['end'])):
                    raise ValueError(f'Invalid end time for {day}: must be HH:MM (24h)')
        return v


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
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return success_response(data=new_data)
