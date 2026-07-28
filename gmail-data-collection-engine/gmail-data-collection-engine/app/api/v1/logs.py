from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

from app.db.session import get_db
from app.models.system_log import SystemLog
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/logs", tags=["logs"], dependencies=[Depends(get_current_user)])


class SystemLogResponse(BaseModel):
    id: str
    level: str
    category: str
    message: str
    details: Optional[dict] = None
    user_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[SystemLogResponse])
def list_logs(
    level: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(SystemLog)
    if level:
        query = query.filter(SystemLog.level == level)
    if category:
        query = query.filter(SystemLog.category == category)
    logs = query.order_by(desc(SystemLog.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return [_to_response(log) for log in logs]


@router.post("/")
def create_log(level: str, category: str, message: str, details: Optional[dict] = None, db: Session = Depends(get_db)):
    log = SystemLog(level=level, category=category, message=message, details=details)
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"success": True, "id": str(log.id)}


def _to_response(log) -> SystemLogResponse:
    return SystemLogResponse(
        id=str(log.id),
        level=log.level,
        category=log.category,
        message=log.message,
        details=log.details,
        user_id=str(log.user_id) if log.user_id else None,
        created_at=log.created_at,
    )
