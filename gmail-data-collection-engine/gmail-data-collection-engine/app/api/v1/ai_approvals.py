from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.ai_approval import AIApproval
from app.models.email import Email
from app.models.workflow import Workflow
from app.models.prompt_template import PromptTemplate
from app.models.ai_provider import AIProvider
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/ai-approvals", tags=["ai-approvals"], dependencies=[Depends(get_current_user)])

class ApprovalItemResponse(BaseModel):
    id: str
    workflow_id: str
    workflow_name: str
    email_id: str
    email_subject: str
    email_sender: str
    email_body: Optional[str] = None
    generated_content: str
    edited_content: Optional[str] = None
    status: str
    prompt_template_id: Optional[str] = None
    prompt_template_name: Optional[str] = None
    provider_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("/", response_model=List[ApprovalItemResponse])
def list_pending_approvals(db: Session = Depends(get_db)):
    approvals = db.query(AIApproval).order_by(AIApproval.created_at.desc()).all()
    
    if not approvals:
        return []
    
    workflow_ids = list(set(a.workflow_id for a in approvals if a.workflow_id))
    email_ids = list(set(a.email_id for a in approvals if a.email_id))
    pt_ids = list(set(a.prompt_template_id for a in approvals if a.prompt_template_id))
    
    workflows = {str(w.id): w for w in db.query(Workflow).filter(Workflow.id.in_(workflow_ids)).all()} if workflow_ids else {}
    emails = {str(e.id): e for e in db.query(Email).filter(Email.id.in_(email_ids)).all()} if email_ids else {}
    templates = {str(t.id): t for t in db.query(PromptTemplate).filter(PromptTemplate.id.in_(pt_ids)).all()} if pt_ids else {}
    
    results = []
    for a in approvals:
        wf = workflows.get(str(a.workflow_id))
        em = emails.get(str(a.email_id))
        pt = templates.get(str(a.prompt_template_id)) if a.prompt_template_id else None

        provider_name = "AI Provider"
        try:
            if pt:
                provider = db.query(AIProvider).filter(AIProvider.is_enabled == True).order_by(AIProvider.priority.desc()).first()
                if provider:
                    provider_name = f"{provider.name} ({provider.provider_type})"
        except Exception:
            pass

        email_body = ""
        if em:
            email_body = (em.body_text or "")[:500] or (em.snippet or "")[:500]

        results.append(
            ApprovalItemResponse(
                id=str(a.id),
                workflow_id=str(a.workflow_id),
                workflow_name=wf.name if wf else "Workflow",
                email_id=str(a.email_id),
                email_subject=em.subject if em else "(No Subject)",
                email_sender=em.sender_email if em else "(Unknown Sender)",
                email_body=email_body,
                generated_content=a.generated_content,
                edited_content=a.edited_content,
                status=a.status,
                prompt_template_id=str(a.prompt_template_id) if a.prompt_template_id else None,
                prompt_template_name=pt.name if pt else None,
                provider_name=provider_name,
                created_at=a.created_at
            )
        )
    return results

@router.get("/stats")
def approval_stats(db: Session = Depends(get_db)):
    total = db.query(AIApproval).count()
    pending = db.query(AIApproval).filter(AIApproval.status == "pending_review").count()
    approved = db.query(AIApproval).filter(AIApproval.status == "approved").count()
    rejected = db.query(AIApproval).filter(AIApproval.status == "rejected").count()
    return {"total": total, "pending": pending, "approved": approved, "rejected": rejected}

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
    return {"success": True, "message": "Draft Approved", "detail": "Email sending will be available in Sprint 6.", "status": "approved"}

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
    return {"success": True, "message": "Draft Rejected", "status": "rejected"}
