import logging
import re
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.prompt_variable import PromptVariable
from app.repositories.prompt_variable_repository import PromptVariableRepository

logger = logging.getLogger("prompt_variable_service")

NAME_REGEX = re.compile(r'^[a-z][a-z0-9_]*$')
VALID_DATA_TYPES = {'STRING', 'LONG_TEXT', 'EMAIL', 'PHONE', 'DATE', 'TIME', 'URL', 'NUMBER', 'FLOAT', 'BOOLEAN', 'JSON', 'HTML', 'MARKDOWN'}
VALID_SCOPES = {'GLOBAL', 'CATEGORY', 'WORKFLOW', 'PROMPT'}
VALID_ADAPTERS = {'STATIC', 'EMAIL', 'COMPANY', 'CUSTOM'}


class PromptVariableService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PromptVariableRepository(db)

    def list_variables(self, scope: str = None, adapter: str = None, category: str = None) -> List[PromptVariable]:
        if scope:
            return self.repo.get_by_scope(scope)
        if adapter:
            return self.repo.get_by_adapter(adapter)
        if category:
            return self.repo.get_by_category(category)
        return self.repo.get_active()

    def get_variable(self, variable_id: str) -> Optional[PromptVariable]:
        return self.repo.get_by_id(variable_id)

    def get_variable_by_name(self, name: str) -> Optional[PromptVariable]:
        return self.repo.get_by_name(name)

    def get_registry(self) -> List[PromptVariable]:
        return self.repo.get_registry()

    def create_variable(self, data: dict, user_id: str = None) -> PromptVariable:
        self._validate(data)
        if self.repo.name_exists(data['name']):
            raise ValueError(f"Variable name '{data['name']}' already exists")

        variable = self.repo.create(
            name=data['name'],
            display_name=data['display_name'],
            description=data.get('description'),
            data_type=data.get('data_type', 'STRING'),
            scope=data.get('scope', 'GLOBAL'),
            source_adapter=data.get('source_adapter', 'STATIC'),
            source_config=data.get('source_config'),
            default_value=data.get('default_value'),
            is_required=data.get('is_required', False),
            validation_regex=data.get('validation_regex'),
            sample_value=data.get('sample_value'),
            category=data.get('category', 'email'),
            created_by=user_id,
        )

        self.db.commit()
        self.db.refresh(variable)
        logger.info(f"Created prompt variable: {variable.name}")
        return variable

    def update_variable(self, variable_id: str, data: dict, user_id: str = None) -> Optional[PromptVariable]:
        variable = self.repo.get_by_id(variable_id)
        if not variable:
            return None

        if 'name' in data and data['name'] != variable.name:
            raise ValueError("Variable name cannot be changed after creation")

        self._validate(data, partial=True)

        for key, value in data.items():
            if key == 'name':
                continue
            if hasattr(variable, key) and value is not None:
                setattr(variable, key, value)

        self.db.commit()
        self.db.refresh(variable)
        logger.info(f"Updated prompt variable: {variable.name}")
        return variable

    def delete_variable(self, variable_id: str) -> bool:
        variable = self.repo.get_by_id(variable_id)
        if not variable:
            return False
        return self.repo.soft_delete(variable_id)

    def get_adapters(self) -> list:
        return [
            {'name': 'STATIC', 'description': 'Admin-provided static value', 'phase': '2A'},
            {'name': 'EMAIL', 'description': 'Pulled from incoming email fields', 'phase': '3'},
            {'name': 'COMPANY', 'description': 'Pulled from company settings', 'phase': '3'},
            {'name': 'CUSTOM', 'description': 'Custom source (CRM, ERP, Knowledge, Formula - Phase 2B+)', 'phase': '2B+'},
        ]

    def _validate(self, data: dict, partial: bool = False):
        if not partial or 'name' in data:
            if 'name' in data:
                name = data['name']
                if not name or not NAME_REGEX.match(name):
                    raise ValueError("Variable name must be lowercase letters, numbers, and underscores, starting with a letter")
                if len(name) > 100:
                    raise ValueError("Variable name must be 1-100 characters")

        if not partial or 'display_name' in data:
            if 'display_name' in data:
                display = data['display_name']
                if not display or len(display.strip()) < 1 or len(display) > 150:
                    raise ValueError("Display name must be 1-150 characters")

        if 'data_type' in data and data['data_type'] is not None:
            if data['data_type'] not in VALID_DATA_TYPES:
                raise ValueError(f"Data type must be one of: {', '.join(sorted(VALID_DATA_TYPES))}")

        if 'scope' in data and data['scope'] is not None:
            if data['scope'] not in VALID_SCOPES:
                raise ValueError(f"Scope must be one of: {', '.join(sorted(VALID_SCOPES))}")

        if 'source_adapter' in data and data['source_adapter'] is not None:
            if data['source_adapter'] not in VALID_ADAPTERS:
                raise ValueError(f"Source adapter must be one of: {', '.join(sorted(VALID_ADAPTERS))}")

        if 'validation_regex' in data and data['validation_regex'] is not None:
            try:
                re.compile(data['validation_regex'])
            except re.error:
                raise ValueError("Invalid validation regex pattern")
