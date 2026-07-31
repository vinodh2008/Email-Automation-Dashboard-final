import logging
from sqlalchemy.orm import Session
from app.services.variable_resolver import VariableResolver

logger = logging.getLogger("prompt_builder_service")


class PromptBuilderService:
    def __init__(self, db: Session):
        self.db = db
        self.resolver = VariableResolver(db)

    def build(self, prompt_content: str, variable_values: dict, context: dict = None, knowledge_context: str = None) -> dict:
        resolution = self.resolver.resolve(prompt_content, variable_values, context)

        if knowledge_context:
            rendered = resolution.get('rendered_prompt', prompt_content)
            rendered += f"\n\n--- Knowledge Context ---\n{knowledge_context}"
            resolution['rendered_prompt'] = rendered

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

    def validate(self, prompt_content: str, variables: list = None) -> dict:
        """Validate a prompt template. Returns {valid, errors, warnings, suggestions}."""
        errors = []
        warnings = []
        suggestions = []

        if not prompt_content or not prompt_content.strip():
            errors.append("Prompt template is empty")
        elif len(prompt_content) < 50:
            warnings.append("Prompt template is very short (< 50 chars)")
        elif len(prompt_content) > 5000:
            warnings.append("Prompt template is very long (> 5000 chars)")

        detected = self.detect_variables(prompt_content)
        detected_names = {v.get("name", "") if isinstance(v, dict) else getattr(v, "name", "") for v in detected}

        import re
        injection_patterns = [r'\$\{', r'<<', r'>>', r'<script', r'eval\(']
        for pat in injection_patterns:
            if re.search(pat, prompt_content, re.IGNORECASE):
                errors.append(f"Potential injection pattern detected: {pat}")

        var_names = [v.get("name", "") if isinstance(v, dict) else getattr(v, "name", "") for v in (variables or detected)]
        bad_names = [n for n in var_names if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', n)]
        if bad_names:
            errors.append(f"Invalid variable names: {bad_names}")

        if len(detected_names) == 0:
            warnings.append("No variables detected in template")

        estimated_tokens = max(1, len(prompt_content) // 4)
        if estimated_tokens > 3500:
            warnings.append(f"Estimated {estimated_tokens} tokens — close to model limit")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "variables_detected": list(detected_names),
            "estimated_tokens": estimated_tokens,
        }

    def inject_knowledge(self, prompt_content: str, knowledge_context: str, knowledge_var_name: str = "knowledge") -> str:
        """Inject knowledge context into a prompt template."""
        if not knowledge_context:
            return prompt_content

        placeholder = "{" + knowledge_var_name + "}"
        if placeholder in prompt_content:
            return prompt_content.replace(placeholder, knowledge_context)

        return prompt_content + f"\n\n--- Knowledge Context ---\n{knowledge_context}"
