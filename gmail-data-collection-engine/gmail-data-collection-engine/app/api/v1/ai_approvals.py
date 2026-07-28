from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.ai_approval import AIApproval
from app.models.email import Email
from app.models.workflow import Workflow
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/ai-approvals", tags=["ai-approvals"], dependencies=[Depends(get_current_user)])

class ApprovalItemResponse(BaseModel):
    id: str
    workflow_id: str
    workflow_name: str
    email_id: str
    email_subject: str
    email_sender: str
    generated_content: str
    edited_content: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ApprovalItemResponse])
def list_pending_approvals(db: Session = Depends(get_db)):
    approvals = db.query(AIApproval).filter(AIApproval.status == "pending_review").order_by(AIApproval.created_at.desc()).all()
    
    if not approvals:
        return []
    
    workflow_ids = list(set(a.workflow_id for a in approvals if a.workflow_id))
    email_ids = list(set(a.email_id for a in approvals if a.email_id))
    
    workflows = {str(w.id): w for w in db.query(Workflow).filter(Workflow.id.in_(workflow_ids)).all()} if workflow_ids else {}
    emails = {str(e.id): e for e in db.query(Email).filter(Email.id.in_(email_ids)).all()} if email_ids else {}
    
    results = []
    for a in approvals:
        wf = workflows.get(str(a.workflow_id))
        em = emails.get(str(a.email_id))
        results.append(
            ApprovalItemResponse(
                id=str(a.id),
                workflow_id=str(a.workflow_id),
                workflow_name=wf.name if wf else "Workflow",
                email_id=str(a.email_id),
                email_subject=em.subject if em else "(No Subject)",
                email_sender=em.sender_email if em else "(Unknown Sender)",
                generated_content=a.generated_content,
                edited_content=a.edited_content,
                status=a.status,
                created_at=a.created_at
            )
        )
    return results

@router.post("/{approval_id}/approve")
def approve_ai_draft(
    approval_id: str,
    edited_text: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    approval = db.query(AIApproval).filter(AIApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval item not found")
    
    approval.status = "approved"
    if edited_text:
        approval.edited_content = edited_text
    approval.reviewed_by = current_user.get("id")
    approval.reviewed_at = datetime.now(timezone.utc)
    
    db.commit()
    return {"message": "AI draft approved successfully"}

@router.post("/{approval_id}/reject")
def reject_ai_draft(
    approval_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    approval = db.query(AIApproval).filter(AIApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval item not found")
    
    approval.status = "rejected"
    approval.reviewed_by = current_user.get("id")
    approval.reviewed_at = datetime.now(timezone.utc)
    
    db.commit()
    return {"message": "AI draft rejected"}
