import logging
import os
import re
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("ai_service")


def _decrypt_key(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted API key. Returns the plaintext key."""
    if not ciphertext:
        return ciphertext
    try:
        from app.auth.encryption import decrypt_string
        return decrypt_string(ciphertext)
    except Exception:
        return ciphertext


class AIService:
    """
    Provider-neutral AI Service implementing automatic failover.
    Loads provider configuration from the database (ai_providers table).
    Falls back to environment variables if no DB provider is configured.
    """
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")

    def _get_db_providers(self):
        if not self.db:
            return []
        try:
            from app.models.ai_provider import AIProvider
            return self.db.query(AIProvider).filter(
                AIProvider.is_enabled == True
            ).order_by(AIProvider.priority.desc()).all()
        except Exception as e:
            logger.warning(f"Failed to load AI providers from DB: {e}")
            return []

    def render_prompt(self, template_str: str, context: Dict[str, Any]) -> str:
        rendered = template_str
        for key, val in context.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(val or ""))
        unreplaced = re.findall(r"\{\{.*?\}\}", rendered)
        if unreplaced:
            logger.warning(f"[AI_SERVICE] Unreplaced template variables: {unreplaced}")
        rendered = re.sub(r"\{\{.*?\}\}", "", rendered)
        return rendered.strip()

    def validate_prompt(self, template_str: str, variables: list) -> dict:
        issues = []
        variables_in_prompt = set(re.findall(r'\{\{(\w+)\}\}', template_str))
        declared_vars = set(variables)
        undeclared = variables_in_prompt - declared_vars
        unused = declared_vars - variables_in_prompt
        if undeclared:
            issues.append(f"Variables in prompt but not declared: {', '.join(undeclared)}")
        if unused:
            issues.append(f"Declared variables not used in prompt: {', '.join(unused)}")
        return {"valid": len(issues) == 0, "issues": issues}

    def generate_reply(self, prompt: str, system_context: str = "") -> str:
        # 1. Try DB-configured providers
        db_providers = self._get_db_providers()
        for provider in db_providers:
            try:
                result = self._call_provider(provider, prompt, system_context)
                if result:
                    logger.info(f"[AI_SERVICE] Provider '{provider.name}' ({provider.provider_type}) generated response.")
                    return result
            except Exception as e:
                logger.warning(f"[AI_SERVICE] Provider '{provider.name}' failed: {e}")

        # 2. Fallback to env-var OpenAI
        if self.openai_key:
            try:
                import openai
                client = openai.OpenAI(api_key=self.openai_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_context or "You are a professional, helpful customer service assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=800,
                    temperature=0.7
                )
                logger.info("[AI_SERVICE] Env-var OpenAI fallback generated response.")
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"[AI_SERVICE] Env-var OpenAI failed: {e}")

        # 3. Intelligent Production Draft Fallback
        logger.info("[AI_SERVICE] All providers failed. Using static fallback draft.")
        return (
            f"Dear Customer,\n\n"
            f"Thank you for contacting us. We have received your inquiry regarding:\n"
            f"\"{prompt[:140]}...\"\n\n"
            f"Our team is reviewing your request and will follow up with you shortly.\n\n"
            f"Best regards,\nCustomer Support Team"
        )

    def _call_provider(self, provider, prompt: str, system_context: str) -> Optional[str]:
        ptype = provider.provider_type
        if ptype == "openai":
            return self._call_openai(provider, prompt, system_context)
        elif ptype == "gemini":
            return self._call_gemini(provider, prompt, system_context)
        elif ptype == "claude":
            return self._call_claude(provider, prompt, system_context)
        elif ptype == "ollama":
            return self._call_ollama(provider, prompt, system_context)
        elif ptype == "openai_compatible":
            return self._call_openai_compatible(provider, prompt, system_context)
        return None

    def _call_openai(self, provider, prompt, system_context):
        import openai
        api_key = _decrypt_key(provider.api_key_encrypted or "")
        client = openai.OpenAI(api_key=api_key, base_url=provider.base_url)
        response = client.chat.completions.create(
            model=provider.model,
            messages=[
                {"role": "system", "content": system_context or "You are a professional, helpful customer service assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=provider.max_tokens or 800,
            temperature=provider.temperature or 0.7
        )
        return response.choices[0].message.content.strip()

    def _call_gemini(self, provider, prompt, system_context):
        import google.generativeai as genai
        api_key = _decrypt_key(provider.api_key_encrypted or "")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(provider.model)
        full_prompt = f"{system_context}\n\n{prompt}" if system_context else prompt
        response = model.generate_content(full_prompt)
        return response.text

    def _call_claude(self, provider, prompt, system_context):
        import anthropic
        api_key = _decrypt_key(provider.api_key_encrypted or "")
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=provider.model,
            max_tokens=provider.max_tokens or 800,
            system=system_context or "You are a professional, helpful customer service assistant.",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _call_ollama(self, provider, prompt, system_context):
        import requests
        base_url = provider.base_url or "http://localhost:11434"
        resp = requests.post(f"{base_url}/api/generate", json={
            "model": provider.model,
            "prompt": prompt,
            "system": system_context or "",
            "stream": False
        }, timeout=30)
        resp.raise_for_status()
        return resp.json().get("response", "")

    def _call_openai_compatible(self, provider, prompt, system_context):
        import openai
        api_key = _decrypt_key(provider.api_key_encrypted or "")
        client = openai.OpenAI(api_key=api_key or "dummy", base_url=provider.base_url)
        response = client.chat.completions.create(
            model=provider.model,
            messages=[
                {"role": "system", "content": system_context or "You are a professional, helpful customer service assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=provider.max_tokens or 800,
            temperature=provider.temperature or 0.7
        )
        return response.choices[0].message.content.strip()
