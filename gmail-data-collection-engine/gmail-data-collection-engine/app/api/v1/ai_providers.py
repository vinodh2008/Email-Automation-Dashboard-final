from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.services.ai_provider_service import AIProviderService
from app.services.ai_health_service import AIHealthService
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/ai-providers", tags=["ai-providers"], dependencies=[Depends(get_current_user)])


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
def create_provider(payload: AIProviderCreate, request: Request, db: Session = Depends(get_db)):
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
        ip_address=request.client.host if request.client else None,
    )
    return _to_response(provider)


@router.get("/health")
def get_providers_health(db: Session = Depends(get_db)):
    health_service = AIHealthService(db)
    data = health_service.get_all_health()
    return success_response(data=data)


@router.get("/{provider_id}", response_model=AIProviderResponse)
def get_provider(provider_id: str, db: Session = Depends(get_db)):
    service = AIProviderService(db)
    provider = service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _to_response(provider)


@router.put("/{provider_id}", response_model=AIProviderResponse)
def update_provider(provider_id: str, payload: AIProviderUpdate, request: Request, db: Session = Depends(get_db)):
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
        ip_address=request.client.host if request.client else None,
    )
    return _to_response(provider)


@router.delete("/{provider_id}")
def delete_provider(provider_id: str, request: Request, db: Session = Depends(get_db)):
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
        ip_address=request.client.host if request.client else None,
    )
    return {"success": True, "message": "Provider deleted"}


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
        health_score=getattr(p, 'health_score', None),
        created_at=p.created_at,
        updated_at=p.updated_at,
    )
