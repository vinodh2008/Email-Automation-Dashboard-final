import logging
from sqlalchemy.orm import Session
from app.services.variable_resolver import VariableResolver
from app.services.cost_estimator import CostEstimator

logger = logging.getLogger("prompt_builder_service")


class PromptBuilderService:
    def __init__(self, db: Session):
        self.db = db
        self.resolver = VariableResolver(db)
        self.cost_estimator = CostEstimator()

    def build(self, prompt_content: str, variable_values: dict, provider_type: str = None, model: str = None, context: dict = None) -> dict:
        resolution = self.resolver.resolve(prompt_content, variable_values, context)

        cost = self.cost_estimator.estimate(
            resolution['rendered_prompt'],
            provider_type=provider_type,
            model=model,
        )

        return {
            'rendered_prompt': resolution['rendered_prompt'],
            'variables_used': resolution['variables_used'],
            'variables_missing': resolution['variables_missing'],
            'variables_unknown': resolution['variables_unknown'],
            'warnings': resolution['warnings'],
            'variables_in_prompt': resolution['variables_in_prompt'],
            'prompt_length_chars': cost['prompt_length_chars'],
            'estimated_tokens': cost['estimated_tokens'],
            'estimated_cost_usd': cost['estimated_cost_usd'],
            'provider_type': cost['provider_type'],
            'model': cost['model'],
        }

    def detect_variables(self, prompt_content: str) -> list:
        return self.resolver.detect_variables(prompt_content)

    def estimate_cost(self, text: str, provider_type: str = None, model: str = None) -> dict:
        return self.cost_estimator.estimate(text, provider_type, model)
