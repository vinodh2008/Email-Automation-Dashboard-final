import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.category_workflow_mapping import CategoryWorkflowMapping
from app.repositories.base_repository import BaseRepository

logger = logging.getLogger("category_workflow_repository")


class CategoryWorkflowRepository(BaseRepository):
    def __init__(self, db: Session):
        super().__init__(db, CategoryWorkflowMapping)

    def get_by_category(self, category_id: str) -> List[CategoryWorkflowMapping]:
        return self.db.query(CategoryWorkflowMapping).filter(
            CategoryWorkflowMapping.business_category_id == category_id,
            CategoryWorkflowMapping.is_active == True
        ).order_by(CategoryWorkflowMapping.priority.asc()).all()

    def get_by_workflow(self, workflow_id: str) -> List[CategoryWorkflowMapping]:
        return self.db.query(CategoryWorkflowMapping).filter(
            CategoryWorkflowMapping.workflow_id == workflow_id,
            CategoryWorkflowMapping.is_active == True
        ).all()

    def pair_exists(self, category_id: str, workflow_id: str, exclude_id: str = None) -> bool:
        query = self.db.query(CategoryWorkflowMapping).filter(
            CategoryWorkflowMapping.business_category_id == category_id,
            CategoryWorkflowMapping.workflow_id == workflow_id
        )
        if exclude_id:
            query = query.filter(CategoryWorkflowMapping.id != exclude_id)
        return query.first() is not None

    def count_by_category(self, category_id: str) -> int:
        return self.db.query(CategoryWorkflowMapping).filter(
            CategoryWorkflowMapping.business_category_id == category_id,
            CategoryWorkflowMapping.is_active == True
        ).count()
