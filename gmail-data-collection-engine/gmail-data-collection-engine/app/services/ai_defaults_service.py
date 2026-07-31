import json
import logging
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.models.system_settings import SystemSetting

logger = logging.getLogger("ai_defaults_service")

DEFAULT_AI = {
    "default_tone": "professional",
    "creativity_level": 0.7,
    "response_length": "medium",
    "default_language": "en",
    "require_human_approval": True,
    "max_retry_count": 3,
    "max_tokens": 4000,
    "default_model": "",
    "fallback_enabled": True,
}


class AIDefaultsService:
    def __init__(self, db: Session):
        self.db = db

    def get(self) -> dict:
        setting = self.db.query(SystemSetting).filter(SystemSetting.key == "ai_defaults").first()
        if not setting:
            self._seed()
            return dict(DEFAULT_AI)
        return dict(setting.value_json) if setting.value_json else dict(DEFAULT_AI)

    def update(self, data: dict, user_id: Optional[str] = None) -> dict:
        setting = self.db.query(SystemSetting).filter(SystemSetting.key == "ai_defaults").first()
        current = dict(setting.value_json) if setting and setting.value_json else dict(DEFAULT_AI)
        merged = {**current, **{k: v for k, v in data.items() if v is not None}}
        if setting:
            setting.value_json = merged
            setting.updated_by = user_id
        else:
            setting = SystemSetting(
                key="ai_defaults",
                value_json=merged,
                description="Global AI behavior defaults for all workflows",
                category="ai",
                updated_by=user_id,
            )
            self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        logger.info("AI defaults updated")
        return dict(setting.value_json)

    def _seed(self):
        self.db.execute(
            text("INSERT INTO system_settings (key, value_json, description, category) "
                 "VALUES (:key, CAST(:val AS jsonb), :desc, :cat) "
                 "ON CONFLICT (key) DO NOTHING"),
            {"key": "ai_defaults", "val": json.dumps(DEFAULT_AI),
             "desc": "Global AI behavior defaults for all workflows", "cat": "ai"}
        )
        self.db.commit()
