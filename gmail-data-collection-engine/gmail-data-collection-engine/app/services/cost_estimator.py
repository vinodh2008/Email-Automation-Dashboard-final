import logging
from typing import Optional

logger = logging.getLogger("cost_estimator")

PROVIDER_COST_PER_1K_TOKENS = {
    'openai': {'gpt-4.1': 0.02, 'gpt-4.1-mini': 0.0004, 'gpt-4o': 0.005, 'gpt-4o-mini': 0.00015},
    'gemini': {'gemini-2.5-pro': 0.00125, 'gemini-2.5-flash': 0.000075},
    'claude': {'claude-sonnet-4-20250514': 0.003, 'claude-3-5-haiku-20241022': 0.001},
}


class CostEstimator:
    def estimate(self, text: str, provider_type: str = None, model: str = None) -> dict:
        char_count = len(text or '')
        estimated_tokens = max(1, char_count // 4)

        estimated_cost = 0.0
        if provider_type and model:
            costs = PROVIDER_COST_PER_1K_TOKENS.get(provider_type, {})
            price_per_1k = costs.get(model, 0.0)
            estimated_cost = (estimated_tokens / 1000.0) * price_per_1k

        return {
            'prompt_length_chars': char_count,
            'estimated_tokens': estimated_tokens,
            'estimated_cost_usd': round(estimated_cost, 6),
            'provider_type': provider_type,
            'model': model,
        }
