import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.admin_audit_log import AdminAuditLog

logger = logging.getLogger("admin_audit_service")


class AdminAuditService:
    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        entry = AdminAuditLog(
            user_id=user_id,
            user_email=user_email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(entry)
        self.db.commit()
        logger.info(f"Audit: {action} {entity_type} {entity_id or ''}")

    def get_logs(
        self,
        entity_type: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ):
        query = self.db.query(AdminAuditLog)
        if entity_type:
            query = query.filter(AdminAuditLog.entity_type == entity_type)
        if user_id:
            query = query.filter(AdminAuditLog.user_id == user_id)
        total = query.count()
        logs = query.order_by(AdminAuditLog.created_at.desc()).offset(offset).limit(limit).all()
        return logs, total
