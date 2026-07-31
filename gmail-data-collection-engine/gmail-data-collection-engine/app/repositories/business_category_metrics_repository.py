import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.business_category_metrics import BusinessCategoryMetrics

logger = logging.getLogger("business_category_metrics_repository")


class BusinessCategoryMetricsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_category(self, category_id: str) -> Optional[BusinessCategoryMetrics]:
        return self.db.query(BusinessCategoryMetrics).filter(
            BusinessCategoryMetrics.business_category_id == category_id
        ).first()

    def get_or_create(self, category_id: str) -> BusinessCategoryMetrics:
        metrics = self.get_by_category(category_id)
        if not metrics:
            metrics = BusinessCategoryMetrics(business_category_id=category_id)
            self.db.add(metrics)
            self.db.flush()
        return metrics

    def increment_emails_processed(self, category_id: str) -> None:
        from sqlalchemy import func
        metrics = self.get_or_create(category_id)
        metrics.emails_processed = (metrics.emails_processed or 0) + 1
        from datetime import datetime, timezone
        metrics.last_used_at = datetime.now(timezone.utc)
        self.db.flush()

    def increment_drafts_generated(self, category_id: str) -> None:
        metrics = self.get_or_create(category_id)
        metrics.drafts_generated = (metrics.drafts_generated or 0) + 1
        self.db.flush()

    def update_approval_rate(self, category_id: str, approved: bool) -> None:
        metrics = self.get_or_create(category_id)
        current = metrics.approval_rate or 0.0
        total = metrics.drafts_generated or 1
        approved_count = int(current * total / 100.0)
        if approved:
            approved_count += 1
        metrics.approval_rate = round((approved_count / total) * 100, 2) if total > 0 else None
        self.db.flush()

    def to_dict(self, metrics: Optional[BusinessCategoryMetrics]) -> dict:
        if not metrics:
            return {}
        return {
            'emails_processed': metrics.emails_processed or 0,
            'drafts_generated': metrics.drafts_generated or 0,
            'approval_rate': metrics.approval_rate,
            'avg_generation_time_ms': metrics.avg_generation_time_ms,
            'avg_tokens_used': metrics.avg_tokens_used,
            'last_used_at': metrics.last_used_at.isoformat() if metrics.last_used_at else None,
        }
