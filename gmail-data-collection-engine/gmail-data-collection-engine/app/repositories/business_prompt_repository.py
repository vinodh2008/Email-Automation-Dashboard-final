import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.business_prompt_template import BusinessPromptTemplate
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger("business_prompt_repository")


class BusinessPromptRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, BusinessPromptTemplate)

    def get_by_category(self, category_id: str) -> List[BusinessPromptTemplate]:
        return self.db.query(BusinessPromptTemplate).filter(
            BusinessPromptTemplate.business_category_id == category_id,
            BusinessPromptTemplate.is_active == True
        ).order_by(BusinessPromptTemplate.created_at.desc()).all()

    def get_published(self) -> List[BusinessPromptTemplate]:
        return self.db.query(BusinessPromptTemplate).filter(
            BusinessPromptTemplate.status == 'published',
            BusinessPromptTemplate.is_active == True
        ).all()

    def get_drafts(self) -> List[BusinessPromptTemplate]:
        return self.db.query(BusinessPromptTemplate).filter(
            BusinessPromptTemplate.status == 'draft',
            BusinessPromptTemplate.is_active == True
        ).all()

    def get_by_status(self, status: str) -> List[BusinessPromptTemplate]:
        return self.db.query(BusinessPromptTemplate).filter(
            BusinessPromptTemplate.status == status,
            BusinessPromptTemplate.is_active == True
        ).all()

    def count_by_category(self, category_id: str) -> int:
        return self.db.query(BusinessPromptTemplate).filter(
            BusinessPromptTemplate.business_category_id == category_id,
            BusinessPromptTemplate.is_active == True
        ).count()
