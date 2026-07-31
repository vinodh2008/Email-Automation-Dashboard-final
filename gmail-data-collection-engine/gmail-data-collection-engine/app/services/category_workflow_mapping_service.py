import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.category_workflow_mapping import CategoryWorkflowMapping
from app.repositories.category_workflow_repository import CategoryWorkflowRepository

logger = logging.getLogger("category_workflow_mapping_service")


class CategoryWorkflowMappingService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CategoryWorkflowRepository(db)

    def list_mappings(self, category_id: str = None, workflow_id: str = None) -> List[CategoryWorkflowMapping]:
        if category_id:
            return self.repo.get_by_category(category_id)
        if workflow_id:
            return self.repo.get_by_workflow(workflow_id)
        return self.repo.get_active()

    def get_mapping(self, mapping_id: str) -> Optional[CategoryWorkflowMapping]:
        return self.repo.get_by_id(mapping_id)

    def create_mapping(self, data: dict, user_id: str = None) -> CategoryWorkflowMapping:
        self._validate(data)
        if self.repo.pair_exists(data['business_category_id'], data['workflow_id']):
            raise ValueError("This category-workflow mapping already exists")

        mapping = self.repo.create(
            business_category_id=data['business_category_id'],
            workflow_id=data['workflow_id'],
            priority=data.get('priority', 0),
            is_active=data.get('is_active', True),
            created_by=user_id,
        )

        self.db.commit()
        self.db.refresh(mapping)
        logger.info(f"Created category-workflow mapping: {data['business_category_id']} → {data['workflow_id']}")
        return mapping

    def update_mapping(self, mapping_id: str, data: dict, user_id: str = None) -> Optional[CategoryWorkflowMapping]:
        mapping = self.repo.get_by_id(mapping_id)
        if not mapping:
            return None

        for key, value in data.items():
            if key in ('priority', 'is_active') and hasattr(mapping, key) and value is not None:
                setattr(mapping, key, value)

        self.db.commit()
        self.db.refresh(mapping)
        logger.info(f"Updated category-workflow mapping: {mapping_id}")
        return mapping

    def delete_mapping(self, mapping_id: str) -> bool:
        mapping = self.repo.get_by_id(mapping_id)
        if not mapping:
            return False
        self.db.delete(mapping)
        self.db.commit()
        logger.info(f"Deleted category-workflow mapping: {mapping_id}")
        return True

    def _validate(self, data: dict):
        if 'business_category_id' not in data or not data['business_category_id']:
            raise ValueError("Business category ID is required")
        if 'workflow_id' not in data or not data['workflow_id']:
            raise ValueError("Workflow ID is required")
        if 'priority' in data and data['priority'] is not None:
            if not isinstance(data['priority'], int) or data['priority'] < 0:
                raise ValueError("Priority must be a non-negative integer")
