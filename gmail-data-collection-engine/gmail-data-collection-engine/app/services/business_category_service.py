import logging
import re
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from app.models.business_category import BusinessCategory
from app.repositories.business_category_repository import BusinessCategoryRepository
from app.repositories.business_prompt_repository import BusinessPromptRepository
from app.repositories.category_workflow_repository import CategoryWorkflowRepository
from app.repositories.business_category_metrics_repository import BusinessCategoryMetricsRepository

logger = logging.getLogger("business_category_service")

CODE_REGEX = re.compile(r'^[A-Z][A-Z0-9_]*$')
COLOR_REGEX = re.compile(r'^#[0-9A-Fa-f]{6}$')
VALID_STATUSES = {'active', 'inactive', 'archived'}


class BusinessCategoryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BusinessCategoryRepository(db)
        self.prompt_repo = BusinessPromptRepository(db)
        self.mapping_repo = CategoryWorkflowRepository(db)
        self.metrics_repo = BusinessCategoryMetricsRepository(db)

    def list_categories(self) -> List[BusinessCategory]:
        return self.repo.get_by_display_order()

    def get_category(self, category_id: str) -> Optional[BusinessCategory]:
        return self.repo.get_by_id(category_id)

    def get_category_by_code(self, code: str) -> Optional[BusinessCategory]:
        return self.repo.get_by_code(code)

    def create_category(self, data: dict, user_id: str = None) -> BusinessCategory:
        self._validate(data)
        if self.repo.code_exists(data['code']):
            raise ValueError(f"Category code '{data['code']}' already exists")
        if self.repo.name_exists(data['name']):
            raise ValueError(f"Category name '{data['name']}' already exists")

        category = self.repo.create(
            name=data['name'],
            code=data['code'],
            description=data.get('description'),
            priority=data.get('priority', 0),
            display_order=data.get('display_order', 0),
            color=data.get('color', '#6366F1'),
            icon=data.get('icon'),
            owner_user_id=data.get('owner_user_id'),
            status=data.get('status', 'active'),
            is_default=data.get('is_default', False),
            created_by=user_id,
            updated_by=user_id,
            ai_model=data.get('ai_model'),
            ai_temperature=data.get('ai_temperature'),
            ai_max_tokens=data.get('ai_max_tokens'),
            ai_timeout=data.get('ai_timeout'),
            ai_retry_count=data.get('ai_retry_count'),
        )

        if data.get('is_default'):
            self.repo.set_default(str(category.id))

        self.db.commit()
        self.db.refresh(category)
        logger.info(f"Created business category: {category.name} ({category.code})")
        return category

    def update_category(self, category_id: str, data: dict, user_id: str = None) -> Optional[BusinessCategory]:
        category = self.repo.get_by_id(category_id)
        if not category:
            return None

        if 'code' in data and data['code'] != category.code:
            raise ValueError("Category code cannot be changed after creation")

        if 'name' in data and data['name'] != category.name:
            if self.repo.name_exists(data['name'], exclude_id=category_id):
                raise ValueError(f"Category name '{data['name']}' already exists")

        self._validate(data, partial=True)

        for key, value in data.items():
            if key == 'code':
                continue
            if hasattr(category, key) and value is not None:
                setattr(category, key, value)

        category.updated_by = user_id

        if data.get('is_default') and not category.is_default:
            self.repo.set_default(category_id)

        self.db.commit()
        self.db.refresh(category)
        logger.info(f"Updated business category: {category.name}")
        return category

    def delete_category(self, category_id: str) -> bool:
        category = self.repo.get_by_id(category_id)
        if not category:
            return False
        if category.is_default:
            raise ValueError("Cannot delete the default category")

        category.business_category_id = None
        self.db.flush()

        return self.repo.soft_delete(category_id)

    def set_default(self, category_id: str) -> bool:
        return self.repo.set_default(category_id)

    def get_category_prompts(self, category_id: str):
        return self.prompt_repo.get_by_category(category_id)

    def get_category_workflows(self, category_id: str):
        return self.mapping_repo.get_by_category(category_id)

    def get_category_metrics(self, category_id: str) -> dict:
        category = self.repo.get_by_id(category_id)
        if not category:
            return {}
        metrics = self.metrics_repo.get_by_category(category_id)
        return self.metrics_repo.to_dict(metrics)

    def update_ai_config(self, category_id: str, ai_config: dict, user_id: str = None) -> Optional[BusinessCategory]:
        category = self.repo.get_by_id(category_id)
        if not category:
            return None

        if 'ai_model' in ai_config:
            category.ai_model = ai_config['ai_model']
        if 'ai_temperature' in ai_config:
            if ai_config['ai_temperature'] is not None and (ai_config['ai_temperature'] < 0 or ai_config['ai_temperature'] > 2):
                raise ValueError("Temperature must be between 0 and 2")
            category.ai_temperature = ai_config['ai_temperature']
        if 'ai_max_tokens' in ai_config:
            if ai_config['ai_max_tokens'] is not None and (ai_config['ai_max_tokens'] < 1 or ai_config['ai_max_tokens'] > 128000):
                raise ValueError("Max tokens must be between 1 and 128000")
            category.ai_max_tokens = ai_config['ai_max_tokens']
        if 'ai_timeout' in ai_config:
            if ai_config['ai_timeout'] is not None and (ai_config['ai_timeout'] < 1 or ai_config['ai_timeout'] > 300):
                raise ValueError("Timeout must be between 1 and 300 seconds")
            category.ai_timeout = ai_config['ai_timeout']
        if 'ai_retry_count' in ai_config:
            if ai_config['ai_retry_count'] is not None and (ai_config['ai_retry_count'] < 0 or ai_config['ai_retry_count'] > 10):
                raise ValueError("Retry count must be between 0 and 10")
            category.ai_retry_count = ai_config['ai_retry_count']

        category.updated_by = user_id
        self.db.commit()
        self.db.refresh(category)
        logger.info(f"Updated AI config for category: {category.name}")
        return category

    def _validate(self, data: dict, partial: bool = False):
        if not partial or 'name' in data:
            if 'name' in data:
                name = data['name']
                if not name or len(name.strip()) < 1 or len(name) > 150:
                    raise ValueError("Category name must be 1-150 characters")

        if not partial or 'code' in data:
            if 'code' in data:
                code = data['code']
                if not code or not CODE_REGEX.match(code):
                    raise ValueError("Category code must be uppercase letters, numbers, and underscores, starting with a letter")

        if 'color' in data and data['color'] is not None:
            if not COLOR_REGEX.match(data['color']):
                raise ValueError("Color must be a valid hex code (e.g., #6366F1)")

        if 'status' in data and data['status'] is not None:
            if data['status'] not in VALID_STATUSES:
                raise ValueError(f"Status must be one of: {', '.join(sorted(VALID_STATUSES))}")

        if 'priority' in data and data['priority'] is not None:
            if not isinstance(data['priority'], int) or data['priority'] < 0:
                raise ValueError("Priority must be a non-negative integer")

        if 'display_order' in data and data['display_order'] is not None:
            if not isinstance(data['display_order'], int) or data['display_order'] < 0:
                raise ValueError("Display order must be a non-negative integer")
