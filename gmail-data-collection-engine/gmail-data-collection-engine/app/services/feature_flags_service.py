import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.system_settings import SystemSetting

logger = logging.getLogger("feature_flags_service")

DEFAULT_FLAGS = {
    "email_summarization": False,
    "draft_reply_generation": False,
    "rag_enabled": False,
    "business_rules_engine": False,
    "email_sending": False,
    "auto_approval": False,
    "advanced_analytics": False,
    "multi_language_support": False,
}


class FeatureFlagsService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> dict:
        setting = self.db.query(SystemSetting).filter(SystemSetting.key == "feature_flags").first()
        if not setting:
            self._seed()
            return dict(DEFAULT_FLAGS)
        return dict(setting.value_json) if setting.value_json else dict(DEFAULT_FLAGS)

    def get_flag(self, flag_name: str) -> bool:
        flags = self.get_all()
        return flags.get(flag_name, False)

    def update_all(self, data: dict, user_id: Optional[str] = None) -> dict:
        setting = self.db.query(SystemSetting).filter(SystemSetting.key == "feature_flags").first()
        current = dict(setting.value_json) if setting and setting.value_json else dict(DEFAULT_FLAGS)
        merged = {**current, **{k: v for k, v in data.items() if k in DEFAULT_FLAGS}}
        if setting:
            setting.value_json = merged
            setting.updated_by = user_id
        else:
            setting = SystemSetting(
                key="feature_flags",
                value_json=merged,
                description="Platform feature toggles",
                category="features",
                updated_by=user_id,
            )
            self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        logger.info("Feature flags updated")
        return dict(setting.value_json)

    def update_flag(self, flag_name: str, enabled: bool, user_id: Optional[str] = None) -> dict:
        if flag_name not in DEFAULT_FLAGS:
            return {}
        current = self.get_all()
        current[flag_name] = enabled
        return self.update_all(current, user_id)

    def _seed(self):
        existing = self.db.query(SystemSetting).filter(SystemSetting.key == "feature_flags").first()
        if not existing:
            setting = SystemSetting(
                key="feature_flags",
                value_json=DEFAULT_FLAGS,
                description="Platform feature toggles",
                category="features",
            )
            self.db.add(setting)
            self.db.commit()
