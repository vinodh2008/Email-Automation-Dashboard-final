from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_permission
from app.services.admin_audit_service import AdminAuditService
from app.core.responses import success_response

router = APIRouter(prefix="/audit-log", tags=["audit-log"], dependencies=[Depends(get_current_user)])


@router.get("/")
def get_audit_logs(
    entity_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("view_users")),
):
    service = AdminAuditService(db)
    logs, total = service.get_logs(
        entity_type=entity_type,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    result = []
    for log in logs:
        result.append({
            "id": str(log.id),
            "user_email": log.user_email,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "old_value": log.old_value,
            "new_value": log.new_value,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return success_response(data={"items": result, "total": total, "limit": limit, "offset": offset})
