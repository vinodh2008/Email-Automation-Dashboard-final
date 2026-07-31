import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.prompt_template_version import PromptTemplateVersion
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger("prompt_version_repository")


class PromptVersionRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, PromptTemplateVersion)

    def get_versions(self, template_id: str) -> List[PromptTemplateVersion]:
        return self.db.query(PromptTemplateVersion).filter(
            PromptTemplateVersion.base_template_id == template_id
        ).order_by(PromptTemplateVersion.version_number.desc()).all()

    def get_version(self, template_id: str, version_number: int) -> Optional[PromptTemplateVersion]:
        return self.db.query(PromptTemplateVersion).filter(
            PromptTemplateVersion.base_template_id == template_id,
            PromptTemplateVersion.version_number == version_number
        ).first()

    def get_latest_version(self, template_id: str) -> Optional[PromptTemplateVersion]:
        return self.db.query(PromptTemplateVersion).filter(
            PromptTemplateVersion.base_template_id == template_id
        ).order_by(PromptTemplateVersion.version_number.desc()).first()

    def get_published_version(self, template_id: str) -> Optional[PromptTemplateVersion]:
        return self.db.query(PromptTemplateVersion).filter(
            PromptTemplateVersion.base_template_id == template_id,
            PromptTemplateVersion.status == 'published'
        ).first()

    def max_version(self, template_id: str) -> int:
        from sqlalchemy import func
        result = self.db.query(func.max(PromptTemplateVersion.version_number)).filter(
            PromptTemplateVersion.base_template_id == template_id
        ).scalar()
        return result or 0
