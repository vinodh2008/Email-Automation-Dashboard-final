import logging
import json
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.prompt_sandbox_session import PromptSandboxSession
from app.models.business_prompt_template import BusinessPromptTemplate
from app.models.prompt_template_version import PromptTemplateVersion
from app.services.prompt_builder_service import PromptBuilderService
from app.services.company_settings_service import CompanySettingsService
from app.repositories.prompt_version_repository import PromptVersionRepository
from app.repositories.business_prompt_repository import BusinessPromptRepository

logger = logging.getLogger("prompt_sandbox_service")


class PromptSandboxService:
    def __init__(self, db: Session):
        self.db = db
        self.builder = PromptBuilderService(db)
        self.version_repo = PromptVersionRepository(db)
        self.prompt_repo = BusinessPromptRepository(db)
        self.company_service = CompanySettingsService(db)

    def run_test(self, template_id: str, variable_values: dict, template_version: int = None, user_id: str = None) -> dict:
        template = self.prompt_repo.get_by_id(template_id) if template_id else None
        prompt_content = None

        if template:
            if template_version:
                version = self.version_repo.get_version(template_id, template_version)
                if version:
                    prompt_content = version.prompt_content
            else:
                prompt_content = template.prompt_content

        if not prompt_content:
            raise ValueError("No prompt content found for testing")

        provider_snapshot = self._get_provider_snapshot()
        company_snapshot = self._get_company_snapshot()
        variables_snapshot = self._get_variables_snapshot()

        build_result = self.builder.build(
            prompt_content=prompt_content,
            variable_values=variable_values,
            provider_type=provider_snapshot.get('provider_type'),
            model=provider_snapshot.get('model'),
        )

        session = self.db.query(PromptSandboxSession).filter(
            PromptSandboxSession.template_id == template_id,
            PromptSandboxSession.status == 'pending'
        ).first()

        if not session:
            session = PromptSandboxSession(
                template_id=template_id,
                template_version=template_version or (template.current_version if template else None),
                created_by=user_id,
            )
            self.db.add(session)

        session.variable_values = variable_values
        session.variables_snapshot = variables_snapshot
        session.company_settings_snapshot = company_snapshot
        session.provider_snapshot = provider_snapshot
        session.rendered_prompt = build_result['rendered_prompt']
        session.validation_result = {
            'valid': len(build_result['variables_missing']) == 0 and len(build_result['variables_unknown']) == 0,
            'missing_count': len(build_result['variables_missing']),
            'unknown_count': len(build_result['variables_unknown']),
        }
        session.variables_used = build_result['variables_used']
        session.variables_missing = build_result['variables_missing']
        session.variables_unknown = build_result['variables_unknown']
        session.prompt_length_chars = build_result['prompt_length_chars']
        session.estimated_tokens = build_result['estimated_tokens']
        session.estimated_cost_usd = build_result['estimated_cost_usd']
        session.warnings = build_result['warnings']
        session.status = 'completed'

        if template:
            latest_version = self.version_repo.get_latest_version(template_id)
            if latest_version:
                latest_version.sandbox_result = {
                    'rendered_prompt': build_result['rendered_prompt'],
                    'variables_used': list(build_result['variables_used'].keys()),
                    'variables_missing': build_result['variables_missing'],
                    'variables_unknown': build_result['variables_unknown'],
                    'estimated_tokens': build_result['estimated_tokens'],
                    'estimated_cost_usd': build_result['estimated_cost_usd'],
                    'tested_at': datetime.now(timezone.utc).isoformat(),
                }

        self.db.commit()
        self.db.refresh(session)

        return {
            'session_id': str(session.id),
            'rendered_prompt': build_result['rendered_prompt'],
            'variables_used': build_result['variables_used'],
            'variables_missing': build_result['variables_missing'],
            'variables_unknown': build_result['variables_unknown'],
            'warnings': build_result['warnings'],
            'prompt_length_chars': build_result['prompt_length_chars'],
            'estimated_tokens': build_result['estimated_tokens'],
            'estimated_cost_usd': build_result['estimated_cost_usd'],
            'validation_result': session.validation_result,
            'snapshots': {
                'variables': bool(variables_snapshot),
                'company': bool(company_snapshot),
                'provider': bool(provider_snapshot),
            },
        }

    def validate_only(self, prompt_content: str, variable_values: dict) -> dict:
        return self.builder.build(prompt_content, variable_values)

    def get_history(self, user_id: str = None, limit: int = 20) -> List[dict]:
        query = self.db.query(PromptSandboxSession)
        if user_id:
            query = query.filter(PromptSandboxSession.created_by == user_id)
        sessions = query.order_by(PromptSandboxSession.created_at.desc()).limit(limit).all()

        return [{
            'id': str(s.id),
            'template_id': str(s.template_id) if s.template_id else None,
            'template_version': s.template_version,
            'status': s.status,
            'estimated_tokens': s.estimated_tokens,
            'estimated_cost_usd': s.estimated_cost_usd,
            'variables_missing_count': len(s.variables_missing or []),
            'variables_unknown_count': len(s.variables_unknown or []),
            'created_at': s.created_at.isoformat() if s.created_at else None,
        } for s in sessions]

    def get_session(self, session_id: str) -> Optional[dict]:
        session = self.db.query(PromptSandboxSession).filter(PromptSandboxSession.id == session_id).first()
        if not session:
            return None

        return {
            'id': str(session.id),
            'template_id': str(session.template_id) if session.template_id else None,
            'template_version': session.template_version,
            'variable_values': session.variable_values,
            'variables_snapshot': session.variables_snapshot,
            'company_settings_snapshot': session.company_settings_snapshot,
            'provider_snapshot': session.provider_snapshot,
            'rendered_prompt': session.rendered_prompt,
            'validation_result': session.validation_result,
            'variables_used': session.variables_used,
            'variables_missing': session.variables_missing,
            'variables_unknown': session.variables_unknown,
            'prompt_length_chars': session.prompt_length_chars,
            'estimated_tokens': session.estimated_tokens,
            'estimated_cost_usd': session.estimated_cost_usd,
            'warnings': session.warnings,
            'status': session.status,
            'created_at': session.created_at.isoformat() if session.created_at else None,
        }

    def _get_provider_snapshot(self) -> dict:
        try:
            from app.models.ai_provider import AIProvider
            provider = self.db.query(AIProvider).filter(AIProvider.is_primary == True, AIProvider.is_enabled == True).first()
            if not provider:
                provider = self.db.query(AIProvider).filter(AIProvider.is_enabled == True).order_by(AIProvider.priority.desc()).first()
            if provider:
                return {
                    'name': provider.name,
                    'provider_type': provider.provider_type,
                    'model': provider.model,
                    'temperature': provider.temperature,
                    'max_tokens': provider.max_tokens,
                }
        except Exception as e:
            logger.warning(f"Could not get provider snapshot: {e}")
        return {}

    def _get_company_snapshot(self) -> dict:
        try:
            return self.company_service.get()
        except Exception as e:
            logger.warning(f"Could not get company snapshot: {e}")
        return {}

    def _get_variables_snapshot(self) -> list:
        try:
            from app.models.prompt_variable import PromptVariable
            variables = self.db.query(PromptVariable).filter(PromptVariable.is_active == True).all()
            return [{
                'name': v.name,
                'display_name': v.display_name,
                'data_type': v.data_type,
                'scope': v.scope,
                'source_adapter': v.source_adapter,
                'is_required': v.is_required,
            } for v in variables]
        except Exception as e:
            logger.warning(f"Could not get variables snapshot: {e}")
        return []
