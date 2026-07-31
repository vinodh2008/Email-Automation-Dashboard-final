from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.services.ai_provider_service import AIProviderService
from app.services.ai_health_service import AIHealthService
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/ai-providers", tags=["ai-providers"], dependencies=[Depends(get_current_user)])

PROVIDER_TYPES = {'openai', 'gemini', 'claude', 'ollama', 'openai_compatible'}


class AIProviderCreate(BaseModel):
    name: str
    provider_type: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    is_enabled: Optional[bool] = True
    is_primary: Optional[bool] = False
    priority: Optional[int] = 0
    max_tokens: Optional[int] = 800
    temperature: Optional[float] = 0.7
    timeout: Optional[int] = 30
    retry_count: Optional[int] = 3

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or len(v.strip()) < 1 or len(v) > 150:
            raise ValueError('Provider name must be 1-150 characters')
        return v.strip()

    @field_validator('provider_type')
    @classmethod
    def validate_provider_type(cls, v):
        if v not in PROVIDER_TYPES:
            raise ValueError(f'Invalid provider type. Must be one of: {", ".join(sorted(PROVIDER_TYPES))}')
        return v

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if v is not None and (v < 0 or v > 2):
            raise ValueError('Temperature must be between 0 and 2')
        return v

    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        if v is not None and (v < 1 or v > 128000):
            raise ValueError('Max tokens must be between 1 and 128000')
        return v

    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v):
        if v is not None and (v < 1 or v > 300):
            raise ValueError('Timeout must be between 1 and 300 seconds')
        return v

    @field_validator('retry_count')
    @classmethod
    def validate_retry(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('Retry count must be between 0 and 10')
        return v


class AIProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_primary: Optional[bool] = None
    priority: Optional[int] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = None
    retry_count: Optional[int] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None and (len(v.strip()) < 1 or len(v) > 150):
            raise ValueError('Provider name must be 1-150 characters')
        return v.strip() if v else v

    @field_validator('provider_type')
    @classmethod
    def validate_provider_type(cls, v):
        if v is not None and v not in PROVIDER_TYPES:
            raise ValueError(f'Invalid provider type. Must be one of: {", ".join(sorted(PROVIDER_TYPES))}')
        return v

    @field_validator('temperature')
    @classmethod
    def validate_temperature(cls, v):
        if v is not None and (v < 0 or v > 2):
            raise ValueError('Temperature must be between 0 and 2')
        return v

    @field_validator('max_tokens')
    @classmethod
    def validate_max_tokens(cls, v):
        if v is not None and (v < 1 or v > 128000):
            raise ValueError('Max tokens must be between 1 and 128000')
        return v

    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v):
        if v is not None and (v < 1 or v > 300):
            raise ValueError('Timeout must be between 1 and 300 seconds')
        return v

    @field_validator('retry_count')
    @classmethod
    def validate_retry(cls, v):
        if v is not None and (v < 0 or v > 10):
            raise ValueError('Retry count must be between 0 and 10')
        return v


class AIProviderResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    model: str
    api_key_set: bool
    base_url: Optional[str] = None
    is_enabled: bool
    is_primary: bool
    priority: int
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = None
    retry_count: Optional[int] = None
    status: str
    last_tested_at: Optional[datetime] = None
    last_error: Optional[str] = None
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    avg_latency_ms: Optional[int] = None
    latency_ms: Optional[int] = None
    health_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[AIProviderResponse])
def list_providers(db: Session = Depends(get_db)):
    service = AIProviderService(db)
    providers = service.get_providers()
    return [_to_response(p) for p in providers]


@router.post("/", response_model=AIProviderResponse)
def create_provider(payload: AIProviderCreate, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = AIProviderService(db)
    data = payload.model_dump()
    if data.get("api_key"):
        data["api_key_encrypted"] = data.pop("api_key")
    else:
        data.pop("api_key", None)
    data["default_model"] = data.get("model", "")
    provider = service.create_provider(data)
    from app.auth.dependencies import get_current_user
    audit = AdminAuditService(db)
    audit.log(
        action="create",
        entity_type="ai_provider",
        entity_id=str(provider.id),
        new_value={"name": provider.name, "provider_type": provider.provider_type, "model": provider.model},
        user_id=current_user.get("id"),
        user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return _to_response(provider)


@router.get("/health")
def get_providers_health(db: Session = Depends(get_db)):
    health_service = AIHealthService(db)
    data = health_service.get_all_health()
    return success_response(data=data)


@router.get("/metrics")
def get_ai_metrics(db: Session = Depends(get_db)):
    service = AIProviderService(db)
    health_service = AIHealthService(db)
    providers = service.get_all_providers()
    health_data = health_service.get_all_health()

    total_requests = sum(h.get("total_requests", 0) for h in health_data)
    total_success = sum(h.get("successful_requests", 0) for h in health_data)
    total_failed = sum(h.get("failed_requests", 0) for h in health_data)
    total_tokens = sum(h.get("total_tokens_used", 0) for h in health_data)
    latencies = [h["avg_latency_ms"] for h in health_data if h.get("avg_latency_ms")]
    avg_latency = int(sum(latencies) / len(latencies)) if latencies else 0

    estimated_cost = 0.0
    for p in providers:
        if not p.is_enabled:
            continue
        from app.services.ai_provider_service import PROVIDER_COST_PER_1K_TOKENS
        costs = PROVIDER_COST_PER_1K_TOKENS.get(p.provider_type, {})
        model_name = getattr(p, 'model', None) or getattr(p, 'default_model', '') or ''
        price_per_1k = costs.get(model_name, 0.0)
        tokens = getattr(p, 'total_tokens_used', 0) or 0
        estimated_cost += (tokens / 1000.0) * price_per_1k

    active_providers = sum(1 for p in providers if p.is_enabled)
    error_providers = sum(1 for h in health_data if h.get("status") == "error")

    per_provider = []
    for p in providers:
        h = next((x for x in health_data if x["id"] == str(p.id)), {})
        from app.services.ai_provider_service import PROVIDER_COST_PER_1K_TOKENS
        costs = PROVIDER_COST_PER_1K_TOKENS.get(p.provider_type, {})
        model_name = getattr(p, 'model', None) or getattr(p, 'default_model', '') or ''
        price_per_1k = costs.get(model_name, 0.0)
        tokens = h.get("total_tokens_used", 0)
        per_provider.append({
            "id": h.get("id"),
            "name": h.get("name"),
            "provider_type": h.get("provider_type"),
            "model": model_name,
            "total_requests": h.get("total_requests", 0),
            "successful_requests": h.get("successful_requests", 0),
            "failed_requests": h.get("failed_requests", 0),
            "total_tokens_used": tokens,
            "avg_latency_ms": h.get("avg_latency_ms"),
            "health_score": h.get("health_score", 100),
            "uptime_percent": h.get("uptime_percent", 100),
            "estimated_cost": round((tokens / 1000.0) * price_per_1k, 4),
            "status": h.get("status", "unknown"),
        })

    return success_response(data={
        "summary": {
            "total_requests": total_requests,
            "successful_requests": total_success,
            "failed_requests": total_failed,
            "success_rate": round((total_success / total_requests * 100), 1) if total_requests > 0 else 100.0,
            "total_tokens_used": total_tokens,
            "avg_latency_ms": avg_latency,
            "estimated_cost_usd": round(estimated_cost, 4),
            "active_providers": active_providers,
            "error_providers": error_providers,
        },
        "providers": per_provider,
    })


@router.get("/{provider_id}", response_model=AIProviderResponse)
def get_provider(provider_id: str, db: Session = Depends(get_db)):
    service = AIProviderService(db)
    provider = service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _to_response(provider)


@router.put("/{provider_id}", response_model=AIProviderResponse)
def update_provider(provider_id: str, payload: AIProviderUpdate, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = AIProviderService(db)
    old_provider = service.get_provider(provider_id)
    if not old_provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    old_data = {"name": old_provider.name, "provider_type": old_provider.provider_type, "model": old_provider.model}
    data = payload.model_dump(exclude_unset=True)
    if data.get("api_key"):
        data["api_key_encrypted"] = data.pop("api_key")
    else:
        data.pop("api_key", None)
    if "model" in data:
        data["default_model"] = data["model"]
    provider = service.update_provider(provider_id, data)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    audit = AdminAuditService(db)
    audit.log(
        action="update",
        entity_type="ai_provider",
        entity_id=str(provider.id),
        old_value=old_data,
        new_value={"name": provider.name, "provider_type": provider.provider_type, "model": provider.model},
        user_id=current_user.get("id"),
        user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return _to_response(provider)


@router.delete("/{provider_id}")
def delete_provider(provider_id: str, request: Request, db: Session = Depends(get_db), current_user: dict = Depends(require_permission("update_users"))):
    service = AIProviderService(db)
    provider = service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    old_data = {"name": provider.name, "provider_type": provider.provider_type}
    if not service.delete_provider(provider_id):
        raise HTTPException(status_code=404, detail="Provider not found")
    audit = AdminAuditService(db)
    audit.log(
        action="delete",
        entity_type="ai_provider",
        entity_id=provider_id,
        old_value=old_data,
        user_id=current_user.get("id"),
        user_email=current_user.get("email"),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.commit()
    return success_response(message="Provider deleted")


@router.post("/{provider_id}/test")
def test_provider(provider_id: str, db: Session = Depends(get_db)):
    service = AIProviderService(db)
    health = AIHealthService(db)
    result = service.test_provider(provider_id)
    if not result["success"] and "not found" in result.get("error", "").lower():
        raise HTTPException(status_code=404, detail="Provider not found")
    latency = result.get("latency_ms", 0) or 0
    health.record_test(provider_id, result["success"], latency)
    return success_response(data=result)


@router.post("/test-all")
def test_all_providers(db: Session = Depends(get_db)):
    service = AIProviderService(db)
    health = AIHealthService(db)
    providers = service.get_providers()
    results = []
    for p in providers:
        result = service.test_provider(str(p.id))
        latency = result.get("latency_ms", 0) or 0
        health.record_test(str(p.id), result["success"], latency)
        results.append({"id": str(p.id), "name": p.name, **result})
    return success_response(data=results)


def _to_response(p) -> AIProviderResponse:
    model_name = getattr(p, 'model', None) or getattr(p, 'default_model', None) or 'unknown'
    api_key_val = getattr(p, 'api_key_encrypted', None) or getattr(p, 'api_key', None)
    return AIProviderResponse(
        id=str(p.id),
        name=p.name,
        provider_type=p.provider_type,
        model=model_name,
        api_key_set=bool(api_key_val),
        base_url=p.base_url,
        is_enabled=p.is_enabled,
        is_primary=getattr(p, 'is_primary', False) or False,
        priority=p.priority,
        max_tokens=getattr(p, 'max_tokens', None),
        temperature=getattr(p, 'temperature', None),
        timeout=getattr(p, 'timeout', 30),
        retry_count=getattr(p, 'retry_count', 3),
        status=p.status,
        last_tested_at=p.last_tested_at,
        last_error=getattr(p, 'last_error', None),
        total_requests=getattr(p, 'total_requests', 0) or 0,
        successful_requests=getattr(p, 'successful_requests', 0) or 0,
        failed_requests=getattr(p, 'failed_requests', 0) or 0,
        total_tokens_used=getattr(p, 'total_tokens_used', 0) or 0,
        avg_latency_ms=getattr(p, 'avg_latency_ms', None),
        latency_ms=getattr(p, 'latency_ms', None),
        health_score=max(0.0, min(100.0, getattr(p, 'health_score', None) or 0.0)),
        created_at=p.created_at,
        updated_at=p.updated_at,
    )
