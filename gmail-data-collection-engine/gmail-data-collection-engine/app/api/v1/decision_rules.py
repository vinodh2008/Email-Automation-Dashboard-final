from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.db.session import get_db
from app.auth.dependencies import get_current_user
from app.services.decision_service import DecisionService
from app.core.responses import success_response

router = APIRouter(prefix="/decision-rules", tags=["decision-rules"], dependencies=[Depends(get_current_user)])


class DecisionRuleCreate(BaseModel):
    business_category_id: str
    name: str
    description: Optional[str] = None
    is_enabled: Optional[bool] = True
    priority: Optional[int] = 0
    min_confidence: Optional[float] = 0.9
    max_risk_level: Optional[str] = "low"
    max_email_value: Optional[float] = None
    sender_whitelist: Optional[List[str]] = []
    category_codes: Optional[List[str]] = []
    action: Optional[str] = "escalate"
    approval_chain: Optional[List] = []


class DecisionRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    priority: Optional[int] = None
    min_confidence: Optional[float] = None
    max_risk_level: Optional[str] = None
    max_email_value: Optional[float] = None
    sender_whitelist: Optional[List[str]] = None
    category_codes: Optional[List[str]] = None
    action: Optional[str] = None
    approval_chain: Optional[List] = None


@router.get("/")
def list_rules(category_id: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        svc = DecisionService(db)
        if category_id:
            rules = svc.get_rules(category_id)
        else:
            rules = []
        return success_response(data=rules)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/")
def create_rule(rule_data: DecisionRuleCreate, db: Session = Depends(get_db)):
    try:
        svc = DecisionService(db)
        result = svc.create_rule(rule_data.business_category_id, rule_data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create rule")
        return success_response(data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{rule_id}")
def update_rule(rule_id: str, rule_data: DecisionRuleUpdate, db: Session = Depends(get_db)):
    try:
        svc = DecisionService(db)
        result = svc.update_rule(rule_id, rule_data.model_dump(exclude_unset=True))
        if not result:
            raise HTTPException(status_code=404, detail="Rule not found")
        return success_response(data={"status": "updated"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{rule_id}")
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    try:
        svc = DecisionService(db)
        result = svc.delete_rule(rule_id)
        if not result:
            raise HTTPException(status_code=404, detail="Rule not found")
        return success_response(data={"status": "deleted"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
