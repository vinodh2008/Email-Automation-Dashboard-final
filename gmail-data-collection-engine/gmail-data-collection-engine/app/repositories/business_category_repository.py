import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.business_category import BusinessCategory
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger("business_category_repository")


class BusinessCategoryRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, BusinessCategory)

    def get_by_code(self, code: str) -> Optional[BusinessCategory]:
        return self.db.query(BusinessCategory).filter(
            BusinessCategory.code == code,
            BusinessCategory.is_active == True
        ).first()

    def get_default(self) -> Optional[BusinessCategory]:
        return self.db.query(BusinessCategory).filter(
            BusinessCategory.is_default == True,
            BusinessCategory.is_active == True
        ).first()

    def set_default(self, category_id: str) -> bool:
        self.db.execute(
            text("UPDATE business_categories SET is_default = false WHERE is_default = true")
        )
        category = self.get_by_id(category_id)
        if not category:
            return False
        category.is_default = True
        self.db.flush()
        return True

    def get_by_priority(self) -> List[BusinessCategory]:
        return self.db.query(BusinessCategory).filter(
            BusinessCategory.is_active == True,
            BusinessCategory.status == 'active'
        ).order_by(BusinessCategory.priority.asc()).all()

    def get_by_display_order(self) -> List[BusinessCategory]:
        return self.db.query(BusinessCategory).filter(
            BusinessCategory.is_active == True
        ).order_by(BusinessCategory.display_order.asc()).all()

    def code_exists(self, code: str, exclude_id: str = None) -> bool:
        query = self.db.query(BusinessCategory).filter(BusinessCategory.code == code)
        if exclude_id:
            query = query.filter(BusinessCategory.id != exclude_id)
        return query.first() is not None

    def name_exists(self, name: str, exclude_id: str = None) -> bool:
        query = self.db.query(BusinessCategory).filter(BusinessCategory.name == name)
        if exclude_id:
            query = query.filter(BusinessCategory.id != exclude_id)
        return query.first() is not None
