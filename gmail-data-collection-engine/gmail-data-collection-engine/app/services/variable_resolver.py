import logging
import re
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.prompt_variable import PromptVariable
from app.repositories.prompt_variable_repository import PromptVariableRepository

logger = logging.getLogger("variable_resolver")

VAR_PATTERN = re.compile(r'\{\{(\w+)\}\}')


class VariableResolver:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PromptVariableRepository(db)

    def resolve(self, prompt_content: str, variable_values: dict, context: dict = None) -> dict:
        variables_in_prompt = list(set(VAR_PATTERN.findall(prompt_content or '')))
        registry = {v.name: v for v in self.repo.get_registry()}
        context = context or {}

        used = {}
        missing = []
        unknown = []
        warnings = []

        for var_name in variables_in_prompt:
            if var_name not in registry:
                unknown.append(var_name)
                warnings.append(f"Unknown variable: {var_name}")
                continue

            var_def = registry[var_name]
            value = variable_values.get(var_name)

            if value is None or value == '':
                if var_def.default_value:
                    value = var_def.default_value
                    warnings.append(f"Using default value for {var_name}")
                elif var_def.is_required:
                    missing.append(var_name)
                    continue
                else:
                    value = ''
                    warnings.append(f"Optional variable {var_name} not provided")

            if var_def.validation_regex:
                try:
                    if not re.match(var_def.validation_regex, str(value)):
                        warnings.append(f"Value for {var_name} does not match validation pattern")
                except re.error:
                    warnings.append(f"Invalid regex for variable {var_name}")

            used[var_name] = {
                'value': value,
                'display_name': var_def.display_name,
                'data_type': var_def.data_type,
                'scope': var_def.scope,
                'source_adapter': var_def.source_adapter,
            }

        rendered = prompt_content
        for var_name, var_info in used.items():
            rendered = rendered.replace(f'{{{{{var_name}}}}}', str(var_info['value']))

        for var_name in unknown:
            rendered = rendered.replace(f'{{{{{var_name}}}}}', f'[UNKNOWN:{var_name}]')

        return {
            'rendered_prompt': rendered,
            'variables_used': used,
            'variables_missing': missing,
            'variables_unknown': unknown,
            'warnings': warnings,
            'variables_in_prompt': variables_in_prompt,
        }

    def detect_variables(self, prompt_content: str) -> List[str]:
        return list(set(VAR_PATTERN.findall(prompt_content or '')))
