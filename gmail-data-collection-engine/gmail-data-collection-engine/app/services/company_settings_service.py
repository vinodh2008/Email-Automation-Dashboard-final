import json
import logging
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.system_settings import SystemSetting

logger = logging.getLogger("company_settings_service")

DEFAULT_COMPANY = {
    "company_name": "My Company",
    "support_email": "",
    "default_signature": "Best regards,",
    "default_language": "en",
    "timezone": "UTC",
    "business_hours": {
        "monday": {"enabled": True, "start": "09:00", "end": "17:00"},
        "tuesday": {"enabled": True, "start": "09:00", "end": "17:00"},
        "wednesday": {"enabled": True, "start": "09:00", "end": "17:00"},
        "thursday": {"enabled": True, "start": "09:00", "end": "17:00"},
        "friday": {"enabled": True, "start": "09:00", "end": "17:00"},
    },
    "branding": {
        "logo_url": "",
        "primary_color": "#4F46E5",
    },
}


class CompanySettingsService:
    def __init__(self, db: Session):
        self.db = db

    def get(self) -> dict:
        setting = self.db.query(SystemSetting).filter(SystemSetting.key == "company_settings").first()
        if not setting:
            self._seed()
            return dict(DEFAULT_COMPANY)
        return dict(setting.value_json) if setting.value_json else dict(DEFAULT_COMPANY)

    def update(self, data: dict, user_id: Optional[str] = None) -> dict:
        setting = self.db.query(SystemSetting).filter(SystemSetting.key == "company_settings").first()
        current = dict(setting.value_json) if setting and setting.value_json else dict(DEFAULT_COMPANY)
        merged = {**current, **{k: v for k, v in data.items() if v is not None}}
        if setting:
            setting.value_json = merged
            setting.updated_by = user_id
        else:
            setting = SystemSetting(
                key="company_settings",
                value_json=merged,
                description="Company profile, branding, and business hours",
                category="company",
                updated_by=user_id,
            )
            self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        logger.info("Company settings updated")
        return dict(setting.value_json)

    def _seed(self):
        self.db.execute(
            text("INSERT INTO system_settings (key, value_json, description, category) "
                 "VALUES (:key, CAST(:val AS jsonb), :desc, :cat) "
                 "ON CONFLICT (key) DO NOTHING"),
            {"key": "company_settings", "val": json.dumps(DEFAULT_COMPANY),
             "desc": "Company profile, branding, and business hours", "cat": "company"}
        )
        self.db.commit()
