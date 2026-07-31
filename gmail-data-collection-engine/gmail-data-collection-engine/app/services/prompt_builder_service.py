import logging
from sqlalchemy.orm import Session
from app.services.variable_resolver import VariableResolver

logger = logging.getLogger("prompt_builder_service")


class PromptBuilderService:
    def __init__(self, db: Session):
        self.db = db
        self.resolver = VariableResolver(db)

    def build(self, prompt_content: str, variable_values: dict, context: dict = None) -> dict:
        resolution = self.resolver.resolve(prompt_content, variable_values, context)

        return {
            'rendered_prompt': resolution['rendered_prompt'],
            'variables_used': resolution['variables_used'],
            'variables_missing': resolution['variables_missing'],
            'variables_unknown': resolution['variables_unknown'],
            'warnings': resolution['warnings'],
            'variables_in_prompt': resolution['variables_in_prompt'],
            'prompt_length_chars': len(resolution['rendered_prompt'] or ''),
            'estimated_tokens': max(1, len(resolution['rendered_prompt'] or '') // 4),
        }

    def detect_variables(self, prompt_content: str) -> list:
        return self.resolver.detect_variables(prompt_content)
