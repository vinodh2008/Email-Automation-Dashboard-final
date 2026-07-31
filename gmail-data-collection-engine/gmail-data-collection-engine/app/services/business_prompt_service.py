import logging
import re
import json
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.business_prompt_template import BusinessPromptTemplate
from app.models.prompt_template_version import PromptTemplateVersion
from app.repositories.business_prompt_repository import BusinessPromptRepository
from app.repositories.prompt_version_repository import PromptVersionRepository

logger = logging.getLogger("business_prompt_service")

VALID_STATUSES = {'draft', 'testing', 'published', 'archived'}
VALID_TESTING_STATUSES = {'untested', 'testing', 'passed', 'failed'}
VAR_PATTERN = re.compile(r'\{\{(\w+)\}\}')


class BusinessPromptService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BusinessPromptRepository(db)
        self.version_repo = PromptVersionRepository(db)

    def list_templates(self, category_id: str = None, status: str = None) -> List[BusinessPromptTemplate]:
        if category_id:
            return self.repo.get_by_category(category_id)
        if status:
            return self.repo.get_by_status(status)
        return self.repo.get_active()

    def get_template(self, template_id: str) -> Optional[BusinessPromptTemplate]:
        return self.repo.get_by_id(template_id)

    def create_template(self, data: dict, user_id: str = None) -> BusinessPromptTemplate:
        self._validate(data)

        template = self.repo.create(
            business_category_id=data.get('business_category_id'),
            name=data['name'],
            purpose=data.get('purpose'),
            description=data.get('description'),
            prompt_content=data['prompt_content'],
            variables_json=data.get('variables_json', '[]'),
            status='draft',
            testing_status='untested',
            current_version=1,
            created_by=user_id,
            updated_by=user_id,
        )

        version = self.version_repo.create(
            base_template_id=str(template.id),
            version_number=1,
            name=template.name,
            purpose=template.purpose,
            description=template.description,
            prompt_content=template.prompt_content,
            variables_json=template.variables_json,
            status='draft',
            change_summary='Initial creation',
            created_by=user_id,
        )

        self.db.commit()
        self.db.refresh(template)
        logger.info(f"Created business prompt template: {template.name} (v1)")
        return template

    def update_template(self, template_id: str, data: dict, user_id: str = None) -> Optional[BusinessPromptTemplate]:
        template = self.repo.get_by_id(template_id)
        if not template:
            return None
        if template.status not in ('draft', 'testing'):
            raise ValueError("Only draft or testing templates can be edited")

        self._validate(data, partial=True)

        for key, value in data.items():
            if key in ('name', 'purpose', 'description', 'prompt_content', 'variables_json', 'business_category_id'):
                if hasattr(template, key) and value is not None:
                    setattr(template, key, value)

        template.updated_by = user_id
        template.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(template)
        logger.info(f"Updated business prompt template: {template.name}")
        return template

    def delete_template(self, template_id: str) -> bool:
        template = self.repo.get_by_id(template_id)
        if not template:
            return False
        return self.repo.soft_delete(template_id)

    def publish_template(self, template_id: str, change_summary: str, user_id: str = None) -> Optional[dict]:
        template = self.repo.get_by_id(template_id)
        if not template:
            return None
        if template.status == 'published':
            raise ValueError("Template is already published")
        if not template.prompt_content or not template.prompt_content.strip():
            raise ValueError("Cannot publish empty prompt")

        if template.status == 'published':
            old_version = self.version_repo.get_published_version(template_id)
            if old_version:
                old_version.status = 'archived'
                old_version.archived_at = datetime.now(timezone.utc)
                old_version.archived_by = user_id

        new_version_num = template.current_version + 1
        version = self.version_repo.create(
            base_template_id=template_id,
            version_number=new_version_num,
            name=template.name,
            purpose=template.purpose,
            description=template.description,
            prompt_content=template.prompt_content,
            variables_json=template.variables_json,
            status='published',
            change_summary=change_summary,
            published_at=datetime.now(timezone.utc),
            published_by=user_id,
            created_by=user_id,
        )

        template.status = 'published'
        template.current_version = new_version_num
        template.published_version = new_version_num
        template.updated_by = user_id

        self.db.commit()
        self.db.refresh(template)
        logger.info(f"Published template: {template.name} (v{new_version_num})")
        return {'template_id': template_id, 'version': new_version_num}

    def rollback_template(self, template_id: str, target_version: int, user_id: str = None) -> Optional[dict]:
        template = self.repo.get_by_id(template_id)
        if not template:
            return None

        version = self.version_repo.get_version(template_id, target_version)
        if not version:
            raise ValueError(f"Version {target_version} not found")

        if template.status == 'published':
            old_pub = self.version_repo.get_published_version(template_id)
            if old_pub:
                old_pub.status = 'archived'
                old_pub.archived_at = datetime.now(timezone.utc)
                old_pub.archived_by = user_id

        new_version_num = template.current_version + 1
        rollback_version = self.version_repo.create(
            base_template_id=template_id,
            version_number=new_version_num,
            name=version.name,
            purpose=version.purpose,
            description=version.description,
            prompt_content=version.prompt_content,
            variables_json=version.variables_json,
            status='published',
            change_summary=f'Rollback to version {target_version}',
            rollback_from_version=target_version,
            published_at=datetime.now(timezone.utc),
            published_by=user_id,
            created_by=user_id,
        )

        template.name = version.name
        template.purpose = version.purpose
        template.description = version.description
        template.prompt_content = version.prompt_content
        template.variables_json = version.variables_json
        template.status = 'published'
        template.current_version = new_version_num
        template.published_version = new_version_num
        template.updated_by = user_id

        self.db.commit()
        self.db.refresh(template)
        logger.info(f"Rolled back template {template.name} to v{target_version} (now v{new_version_num})")
        return {'template_id': template_id, 'version': new_version_num, 'rollback_from': target_version}

    def archive_template(self, template_id: str, user_id: str = None) -> Optional[dict]:
        template = self.repo.get_by_id(template_id)
        if not template:
            return None
        if template.status != 'published':
            raise ValueError("Only published templates can be archived")

        pub_version = self.version_repo.get_published_version(template_id)
        if pub_version:
            pub_version.status = 'archived'
            pub_version.archived_at = datetime.now(timezone.utc)
            pub_version.archived_by = user_id

        template.status = 'archived'
        template.updated_by = user_id

        self.db.commit()
        self.db.refresh(template)
        logger.info(f"Archived template: {template.name}")
        return {'template_id': template_id, 'status': 'archived'}

    def get_versions(self, template_id: str) -> List[PromptTemplateVersion]:
        return self.version_repo.get_versions(template_id)

    def get_version(self, template_id: str, version_number: int) -> Optional[PromptTemplateVersion]:
        return self.version_repo.get_version(template_id, version_number)

    def clone_template(self, template_id: str, user_id: str = None) -> Optional[BusinessPromptTemplate]:
        template = self.repo.get_by_id(template_id)
        if not template:
            return None

        clone = self.repo.create(
            business_category_id=template.business_category_id,
            name=f"{template.name} (Copy)",
            purpose=template.purpose,
            description=template.description,
            prompt_content=template.prompt_content,
            variables_json=template.variables_json,
            status='draft',
            testing_status='untested',
            current_version=1,
            created_by=user_id,
            updated_by=user_id,
        )

        self.version_repo.create(
            base_template_id=str(clone.id),
            version_number=1,
            name=clone.name,
            purpose=clone.purpose,
            description=clone.description,
            prompt_content=clone.prompt_content,
            variables_json=clone.variables_json,
            status='draft',
            change_summary='Cloned from original',
            created_by=user_id,
        )

        self.db.commit()
        self.db.refresh(clone)
        logger.info(f"Cloned template: {template.name} → {clone.name}")
        return clone

    def detect_variables(self, prompt_content: str) -> list:
        return list(set(VAR_PATTERN.findall(prompt_content or '')))

    def _validate(self, data: dict, partial: bool = False):
        if not partial or 'name' in data:
            if 'name' in data:
                name = data['name']
                if not name or len(name.strip()) < 1 or len(name) > 150:
                    raise ValueError("Template name must be 1-150 characters")

        if not partial or 'prompt_content' in data:
            if 'prompt_content' in data:
                content = data['prompt_content']
                if not content or not content.strip():
                    raise ValueError("Prompt content cannot be empty")
