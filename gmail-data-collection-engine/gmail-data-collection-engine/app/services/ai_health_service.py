import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.ai_provider import AIProvider

logger = logging.getLogger("ai_health_service")


class AIHealthService:
    def __init__(self, db: Session):
        self.db = db

    def record_request(self, provider_id: str, success: bool, latency_ms: int = 0, tokens_used: int = 0):
        provider = self.db.query(AIProvider).filter(AIProvider.id == provider_id).first()
        if not provider:
            return
        provider.total_requests = (provider.total_requests or 0) + 1
        if success:
            provider.successful_requests = (provider.successful_requests or 0) + 1
        else:
            provider.failed_requests = (provider.failed_requests or 0) + 1
        provider.total_tokens_used = (provider.total_tokens_used or 0) + tokens_used
        if latency_ms > 0:
            total_reqs = provider.total_requests or 1
            provider.avg_latency_ms = int(
                ((provider.avg_latency_ms or 0) * (total_reqs - 1) + latency_ms) / total_reqs
            )
        provider.health_score = self._calc_health(provider)
        self.db.commit()

    def record_test(self, provider_id: str, success: bool, latency_ms: int = 0):
        provider = self.db.query(AIProvider).filter(AIProvider.id == provider_id).first()
        if not provider:
            return
        provider.last_tested_at = datetime.now(timezone.utc)
        if success:
            provider.status = "active"
            provider.last_error = None
        else:
            provider.status = "error"
        if latency_ms > 0:
            provider.latency_ms = latency_ms
        provider.health_score = self._calc_health(provider)
        self.db.commit()

    def get_all_health(self):
        providers = self.db.query(AIProvider).all()
        result = []
        for p in providers:
            result.append({
                "id": str(p.id),
                "name": p.name,
                "provider_type": p.provider_type,
                "status": p.status,
                "health_score": p.health_score or 0,
                "total_requests": p.total_requests or 0,
                "successful_requests": p.successful_requests or 0,
                "failed_requests": p.failed_requests or 0,
                "total_tokens_used": p.total_tokens_used or 0,
                "avg_latency_ms": p.avg_latency_ms,
                "latency_ms": p.latency_ms,
                "last_tested_at": p.last_tested_at.isoformat() if p.last_tested_at else None,
                "last_error": p.last_error,
                "uptime_percent": self._calc_uptime(p),
            })
        return result

    def _calc_health(self, provider) -> float:
        total = (provider.total_requests or 0)
        if total == 0:
            return 100.0
        success_rate = ((provider.successful_requests or 0) / total) * 100
        latency = provider.avg_latency_ms or 0
        latency_penalty = min(30, max(0, (latency - 500) / 100))
        score = max(0, min(100, success_rate - latency_penalty))
        return round(score, 1)

    def _calc_uptime(self, provider) -> float:
        total = (provider.total_requests or 0)
        if total == 0:
            return 100.0
        return round(((provider.successful_requests or 0) / total) * 100, 1)
