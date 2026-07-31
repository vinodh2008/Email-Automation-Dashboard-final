import logging
import time
import socket
import ssl
import json
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.ai_provider import AIProvider
from app.auth.encryption import encrypt_string, decrypt_string

logger = logging.getLogger("ai_provider_service")

PROVIDER_COST_PER_1K_TOKENS = {
    "openai": {"gpt-4.1": 0.02, "gpt-4.1-mini": 0.0004, "gpt-4o": 0.005, "gpt-4o-mini": 0.00015, "gpt-4-turbo": 0.01, "o3-mini": 0.0011},
    "gemini": {"gemini-2.5-pro": 0.00125, "gemini-2.5-flash": 0.000075, "gemini-2.0-flash": 0.0001, "gemini-1.5-pro": 0.00125},
    "claude": {"claude-sonnet-4-20250514": 0.003, "claude-3-5-haiku-20241022": 0.001, "claude-3-opus-20240229": 0.015},
    "ollama": {},
    "openai_compatible": {},
}

PROVIDER_BASE_URLS = {
    "openai": "api.openai.com",
    "gemini": "generativelanguage.googleapis.com",
    "claude": "api.anthropic.com",
}


class AIProviderService:
    def __init__(self, db: Session):
        self.db = db

    def get_providers(self, user_id: Optional[str] = None) -> List[AIProvider]:
        query = self.db.query(AIProvider).filter(AIProvider.is_enabled == True)
        if user_id:
            query = query.filter(AIProvider.user_id == user_id)
        return query.order_by(AIProvider.priority.desc(), AIProvider.created_at.desc()).all()

    def get_all_providers(self) -> List[AIProvider]:
        return self.db.query(AIProvider).order_by(AIProvider.priority.desc(), AIProvider.created_at.desc()).all()

    def get_provider(self, provider_id: str) -> Optional[AIProvider]:
        return self.db.query(AIProvider).filter(AIProvider.id == provider_id).first()

    def get_decrypted_api_key(self, provider: AIProvider) -> Optional[str]:
        key = getattr(provider, 'api_key_encrypted', None) or getattr(provider, 'api_key', None)
        if not key:
            return None
        try:
            return decrypt_string(key)
        except Exception:
            return key

    def get_active_provider(self) -> Optional[AIProvider]:
        return self.db.query(AIProvider).filter(
            AIProvider.is_enabled == True,
            AIProvider.is_primary == True
        ).first()

    def get_primary_or_highest_priority(self) -> Optional[AIProvider]:
        primary = self.get_active_provider()
        if primary:
            return primary
        return self.db.query(AIProvider).filter(
            AIProvider.is_enabled == True
        ).order_by(AIProvider.priority.desc()).first()

    def create_provider(self, data: dict) -> AIProvider:
        if data.get("api_key_encrypted"):
            data["api_key_encrypted"] = encrypt_string(data["api_key_encrypted"])
        provider = AIProvider(**data)
        self.db.add(provider)
        if data.get("is_primary"):
            self._clear_other_primaries(provider.id)
        self.db.commit()
        self.db.refresh(provider)
        logger.info(f"Created AI provider: {provider.name} ({provider.provider_type})")
        return provider

    def update_provider(self, provider_id: str, data: dict) -> Optional[AIProvider]:
        provider = self.get_provider(provider_id)
        if not provider:
            return None
        if data.get("api_key_encrypted"):
            data["api_key_encrypted"] = encrypt_string(data["api_key_encrypted"])
        for key, value in data.items():
            if value is not None and hasattr(provider, key):
                setattr(provider, key, value)
        if data.get("is_primary"):
            self._clear_other_primaries(provider_id)
        self.db.commit()
        self.db.refresh(provider)
        logger.info(f"Updated AI provider: {provider.name}")
        return provider

    def delete_provider(self, provider_id: str) -> bool:
        provider = self.get_provider(provider_id)
        if not provider:
            return False
        self.db.delete(provider)
        self.db.commit()
        logger.info(f"Deleted AI provider: {provider.name}")
        return True

    def test_provider(self, provider_id: str) -> dict:
        provider = self.get_provider(provider_id)
        if not provider:
            return {"success": False, "error": "Provider not found", "friendly_message": "Provider not found in system"}

        checks = {}
        total_start = time.time()

        # 1. DNS Resolution
        dns_host = PROVIDER_BASE_URLS.get(provider.provider_type)
        if dns_host:
            dns_start = time.time()
            try:
                socket.getaddrinfo(dns_host, 443)
                checks["dns"] = {"status": "pass", "latency_ms": int((time.time() - dns_start) * 1000)}
            except socket.gaierror:
                checks["dns"] = {"status": "fail", "message": f"Cannot resolve {dns_host}"}
                return self._build_result(provider, checks, False, total_start)
        else:
            checks["dns"] = {"status": "skip", "message": "Custom endpoint"}

        # 2. HTTPS Connectivity
        base_url = provider.base_url or ""
        if base_url:
            https_start = time.time()
            try:
                from urllib.parse import urlparse
                parsed = urlparse(base_url if base_url.startswith("http") else f"https://{base_url}")
                hostname = parsed.hostname
                port = parsed.port or 443
                ctx = ssl.create_default_context()
                with socket.create_connection((hostname, port), timeout=10) as sock:
                    with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                        ssock.getpeercert()
                checks["https"] = {"status": "pass", "latency_ms": int((time.time() - https_start) * 1000)}
            except Exception as e:
                checks["https"] = {"status": "fail", "message": f"HTTPS connection failed: {str(e)[:100]}"}
                return self._build_result(provider, checks, False, total_start)
        else:
            checks["https"] = {"status": "skip", "message": "Using default endpoint"}

        # 3. Authentication + Model + Completion (combined for real providers)
        api_start = time.time()
        try:
            result = self._run_completion(provider)
            api_latency = int((time.time() - api_start) * 1000)
            if result["success"]:
                checks["auth"] = {"status": "pass", "message": "API key valid"}
                checks["model"] = {"status": "pass", "model": provider.model}
                checks["completion"] = {
                    "status": "pass",
                    "response": result.get("response", "")[:200],
                    "tokens_used": result.get("tokens_used", 0),
                    "prompt_tokens": result.get("prompt_tokens", 0),
                    "completion_tokens": result.get("completion_tokens", 0),
                    "latency_ms": api_latency,
                }
            else:
                error_info = self._parse_error(result.get("error", ""))
                checks["auth"] = {"status": "fail", "message": error_info["message"]}
                checks["model"] = {"status": "skip", "message": "Skipped - auth failed"}
                checks["completion"] = {"status": "fail", "message": error_info["message"]}
                return self._build_result(provider, checks, False, total_start, error_info)
        except Exception as e:
            api_latency = int((time.time() - api_start) * 1000)
            error_info = self._parse_error(str(e))
            checks["auth"] = {"status": "fail", "message": error_info["message"]}
            checks["model"] = {"status": "skip", "message": "Skipped - auth failed"}
            checks["completion"] = {"status": "fail", "message": error_info["message"]}
            return self._build_result(provider, checks, False, total_start, error_info)

        # 4. Response Validation
        response_text = result.get("response", "")
        checks["validation"] = {
            "status": "pass" if len(response_text) > 0 else "fail",
            "message": f"Response received ({len(response_text)} chars)",
        }

        # Update provider status
        provider.status = "active"
        provider.last_error = None
        provider.last_tested_at = datetime.now(timezone.utc)
        provider.latency_ms = api_latency
        self.db.commit()

        return self._build_result(provider, checks, True, total_start)

    def _run_completion(self, provider: AIProvider) -> dict:
        api_key = self.get_decrypted_api_key(provider)
        if not api_key:
            return {"success": False, "error": "No API key configured"}

        if provider.provider_type == "openai":
            return self._openai_completion(provider, api_key)
        elif provider.provider_type == "gemini":
            return self._gemini_completion(provider, api_key)
        elif provider.provider_type == "claude":
            return self._claude_completion(provider, api_key)
        elif provider.provider_type == "ollama":
            return self._ollama_completion(provider)
        elif provider.provider_type == "openai_compatible":
            return self._openai_compatible_completion(provider, api_key)
        return {"success": False, "error": f"Unsupported provider: {provider.provider_type}"}

    def _openai_completion(self, provider, api_key):
        import openai
        client = openai.OpenAI(api_key=api_key, base_url=provider.base_url)
        response = client.chat.completions.create(
            model=provider.model,
            messages=[{"role": "user", "content": "Reply with exactly: Connection successful"}],
            max_tokens=10,
            timeout=30,
        )
        usage = response.usage
        return {
            "success": True,
            "response": response.choices[0].message.content,
            "tokens_used": usage.total_tokens if usage else 0,
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
        }

    def _gemini_completion(self, provider, api_key):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(provider.model)
        response = model.generate_content("Reply with exactly: Connection successful")
        return {
            "success": True,
            "response": response.text,
            "tokens_used": getattr(response, 'usage_metadata', {}).get('total_token_count', 0) if hasattr(response, 'usage_metadata') else 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }

    def _claude_completion(self, provider, api_key):
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=provider.model,
            max_tokens=10,
            messages=[{"role": "user", "content": "Reply with exactly: Connection successful"}],
        )
        return {
            "success": True,
            "response": response.content[0].text,
            "tokens_used": (response.usage.input_tokens + response.usage.output_tokens) if response.usage else 0,
            "prompt_tokens": response.usage.input_tokens if response.usage else 0,
            "completion_tokens": response.usage.output_tokens if response.usage else 0,
        }

    def _ollama_completion(self, provider):
        import requests
        base_url = provider.base_url or "http://localhost:11434"
        resp = requests.post(f"{base_url}/api/generate", json={
            "model": provider.model,
            "prompt": "Reply with exactly: Connection successful",
            "stream": False,
        }, timeout=30)
        data = resp.json()
        return {
            "success": True,
            "response": data.get("response", ""),
            "tokens_used": data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
        }

    def _openai_compatible_completion(self, provider, api_key):
        import openai
        client = openai.OpenAI(api_key=api_key or "dummy", base_url=provider.base_url)
        response = client.chat.completions.create(
            model=provider.model,
            messages=[{"role": "user", "content": "Reply with exactly: Connection successful"}],
            max_tokens=10,
            timeout=30,
        )
        usage = response.usage
        return {
            "success": True,
            "response": response.choices[0].message.content,
            "tokens_used": usage.total_tokens if usage else 0,
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
        }

    def _parse_error(self, error_str: str) -> dict:
        error_lower = error_str.lower()

        if "insufficient_quota" in error_lower or "exceeded your current quota" in error_lower:
            return {
                "code": "QUOTA_EXCEEDED",
                "message": "OpenAI returned: Quota exceeded.",
                "reason": "Your OpenAI account has run out of credits or hit its spending limit.",
                "action": "Upgrade your OpenAI plan at platform.openai.com/settings/organization/billing, or add a different provider (Gemini/Claude) as fallback.",
            }
        if "invalid_api_key" in error_lower or "incorrect api key" in error_lower or "authentication" in error_lower:
            return {
                "code": "INVALID_KEY",
                "message": "Authentication failed.",
                "reason": "The API key is invalid or has been revoked.",
                "action": "Generate a new API key from your provider's dashboard and update it in provider settings.",
            }
        if "rate_limit" in error_lower or "429" in error_lower:
            return {
                "code": "RATE_LIMITED",
                "message": "Rate limited by provider.",
                "reason": "Too many requests. The provider is throttling your account.",
                "action": "Wait a few minutes and try again, or upgrade your plan for higher rate limits.",
            }
        if "model_not_found" in error_lower or "model does not exist" in error_lower:
            return {
                "code": "MODEL_NOT_FOUND",
                "message": "Model not available.",
                "reason": f"The requested model is not available for your account.",
                "action": "Check available models in your provider dashboard and update the model name.",
            }
        if "timeout" in error_lower or "timed out" in error_lower:
            return {
                "code": "TIMEOUT",
                "message": "Request timed out.",
                "reason": "The provider did not respond within the timeout period.",
                "action": "Increase the timeout setting or try again later.",
            }
        if "connection" in error_lower or "connect" in error_lower:
            return {
                "code": "CONNECTION_FAILED",
                "message": "Cannot reach provider.",
                "reason": "Network connectivity issue.",
                "action": "Check your internet connection and verify the provider's base URL is correct.",
            }
        if "not found" in error_lower and "404" in error_lower:
            return {
                "code": "ENDPOINT_NOT_FOUND",
                "message": "API endpoint not found.",
                "reason": "The base URL or model name is incorrect.",
                "action": "Verify the base URL matches your provider's API endpoint.",
            }

        return {
            "code": "UNKNOWN_ERROR",
            "message": "AI Connection Failed",
            "reason": error_str[:200],
            "action": "Check provider settings and try again. If the issue persists, contact support.",
        }

    def _build_result(self, provider, checks, success, total_start, error_info=None):
        total_ms = int((time.time() - total_start) * 1000)
        result = {
            "success": success,
            "checks": checks,
            "total_latency_ms": total_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provider": {
                "id": str(provider.id),
                "name": provider.name,
                "type": provider.provider_type,
                "model": provider.model,
            },
        }
        if success:
            completion = checks.get("completion", {})
            result["message"] = "All checks passed"
            result["tokens_used"] = completion.get("tokens_used", 0)
            result["latency_ms"] = completion.get("latency_ms", 0)
        else:
            result["error"] = error_info.get("message", "Unknown error") if error_info else "Connection failed"
            result["friendly_message"] = error_info.get("reason", "Unknown error") if error_info else "Connection failed"
            result["recommended_action"] = error_info.get("action", "Try again") if error_info else "Try again"
            result["error_code"] = error_info.get("code", "UNKNOWN") if error_info else "UNKNOWN"
        return result

    def _clear_other_primaries(self, keep_id):
        self.db.query(AIProvider).filter(
            AIProvider.id != keep_id,
            AIProvider.is_primary == True
        ).update({"is_primary": False})
