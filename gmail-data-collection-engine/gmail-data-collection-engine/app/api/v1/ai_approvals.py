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
from app.core.responses import success_response

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
    
    provider = None
    try:
        provider = db.query(AIProvider).filter(AIProvider.is_enabled == True).order_by(AIProvider.priority.desc()).first()
    except Exception:
        pass
    provider_name = f"{provider.name} ({provider.provider_type})" if provider else "AI Provider"

    results = []
    for a in approvals:
        wf = workflows.get(str(a.workflow_id))
        em = emails.get(str(a.email_id))
        pt = templates.get(str(a.prompt_template_id)) if a.prompt_template_id else None

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


@router.post("/{approval_id}/decide")
def decide_approval(approval_id: str, db: Session = Depends(get_db)):
    try:
        from app.services.decision_service import DecisionService
        approval = db.query(AIApproval).filter(AIApproval.id == approval_id).first()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval item not found")

        email = db.query(Email).filter(Email.id == approval.email_id).first()
        category_id = str(email.business_category_id) if email and email.business_category_id else None

        if not category_id:
            try:
                from app.models.workflow import Workflow
                wf = db.query(Workflow).filter(Workflow.id == approval.workflow_id).first()
                if wf and hasattr(wf, 'business_category_id') and wf.business_category_id:
                    category_id = str(wf.business_category_id)
            except Exception:
                pass

        if not category_id:
            from app.models.business_category import BusinessCategory
            default_cat = db.query(BusinessCategory).filter(
                BusinessCategory.is_default == True
            ).first()
            if default_cat:
                category_id = str(default_cat.id)

        if not category_id:
            raise HTTPException(status_code=400, detail="No category found for decision. Assign a category to the email first.")

        ai_output = {
            "confidence": approval.confidence_score or 0.0,
            "risk_level": "medium",
            "email_value": 0,
            "sender_email": email.sender_email if email else "",
        }

        svc = DecisionService(db)
        decision = svc.decide(approval.email_id, ai_output, category_id)

        import json
        approval.decision_service_output = json.dumps(decision) if isinstance(decision, dict) else decision
        approval.needs_escalation = decision.get("action") == "escalate"
        db.commit()

        return success_response(data=decision)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{approval_id}/send")
def approve_and_send(
    approval_id: str,
    edited_text: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        approval = db.query(AIApproval).filter(AIApproval.id == approval_id).first()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval item not found")

        approval.status = "approved"
        if edited_text:
            approval.edited_content = edited_text
        approval.reviewed_by = current_user.get("id")
        approval.reviewed_at = datetime.now(timezone.utc)
        db.flush()

        from app.services.email_sender_service import EmailSenderService
        svc = EmailSenderService(db)
        result = svc.send_reply(approval_id)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error", "Send failed"))

        db.commit()
        return success_response(data={
            "approval_status": "approved",
            "email_sent": True,
            "gmail_message_id": result.get("gmail_message_id"),
        })
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{approval_id}/regenerate")
def regenerate_draft(
    approval_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        approval = db.query(AIApproval).filter(AIApproval.id == approval_id).first()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval item not found")

        email = db.query(Email).filter(Email.id == approval.email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Original email not found")

        category_id = str(email.business_category_id) if email.business_category_id else None
        if not category_id:
            raise HTTPException(status_code=400, detail="No category assigned to email. Cannot regenerate.")

        from app.services.ai_task_service import AITaskService
        svc = AITaskService(db)
        tasks = svc.get_tasks_for_category(category_id)
        gen_task = next((t for t in tasks if t["task_type"] == "generate_reply"), None)

        if not gen_task:
            raise HTTPException(status_code=404, detail="No generate_reply task found for category")

        result = svc.execute_task(gen_task["id"], str(approval.email_id))
        if not result or result.get("status") != "success":
            raise HTTPException(status_code=400, detail="Regeneration failed")

        approval.generated_content = result.get("generated_content", "")
        approval.status = "pending_review"
        approval.reviewed_by = None
        approval.reviewed_at = None
        db.commit()

        return success_response(data={
            "approval_id": approval_id,
            "new_content": result.get("generated_content", ""),
            "status": "pending_review",
        })
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
