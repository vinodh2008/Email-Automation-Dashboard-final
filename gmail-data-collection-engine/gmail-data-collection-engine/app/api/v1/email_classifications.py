from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.services.category_matcher_service import CategoryMatcherService
from app.core.responses import success_response

router = APIRouter(prefix="/email-classifications", tags=["email-classifications"], dependencies=[Depends(get_current_user)])


@router.get("/")
def get_classification(email_id: str, db: Session = Depends(get_db)):
    try:
        svc = CategoryMatcherService(db)
        classification = svc.get_classification(email_id)
        if not classification:
            raise HTTPException(status_code=404, detail="Classification not found")
        return success_response(data=classification)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reclassify/{email_id}")
def reclassify_email(email_id: str, db: Session = Depends(get_db)):
    try:
        svc = CategoryMatcherService(db)
        result = svc.classify(email_id)
        if not result:
            raise HTTPException(status_code=404, detail="Email not found or classification failed")
        return success_response(data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
