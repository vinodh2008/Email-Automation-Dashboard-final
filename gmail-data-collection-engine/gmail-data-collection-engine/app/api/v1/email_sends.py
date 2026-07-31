from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.services.email_sender_service import EmailSenderService
from app.core.responses import success_response

router = APIRouter(prefix="/email-sends", tags=["email-sends"], dependencies=[Depends(get_current_user)])


@router.post("/{approval_id}/send")
def send_reply(approval_id: str, db: Session = Depends(get_db)):
    try:
        svc = EmailSenderService(db)
        result = svc.send_reply(approval_id)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error", "Send failed"))
        return success_response(data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/batch")
def send_batch(approval_ids: list, db: Session = Depends(get_db)):
    try:
        svc = EmailSenderService(db)
        results = svc.send_batch(approval_ids)
        return success_response(data=results)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/")
def get_send_history(email_id: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    try:
        svc = EmailSenderService(db)
        history = svc.get_send_history(email_id=email_id, limit=limit)
        return success_response(data=history)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
