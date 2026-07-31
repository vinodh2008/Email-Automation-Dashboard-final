from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, load_only
from typing import List
from app.db.session import get_db
from app.models.email import Email
from app.models.workflow import WorkflowExecution, Workflow
from app.schemas.email import EmailListItem, PaginatedEmailResponse, EmailDetailResponse
from sqlalchemy import func, or_
from typing import Dict, Any, Optional
import os
import tempfile
import logging
from openpyxl import Workbook
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from datetime import datetime

from app.auth.dependencies import get_current_user
from app.models.mailbox_account import MailboxAccount
from app.core.responses import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails", tags=["emails"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=PaginatedEmailResponse)
def list_emails(
    status: str = Query("all"),
    search: str = Query(""),
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=100), 
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Email)
    user_id = current_user["id"]
    user_mailbox_ids = [m.id for m in db.query(MailboxAccount).filter(or_(MailboxAccount.user_id == user_id, MailboxAccount.user_id == None)).all()]
    if user_mailbox_ids:
        query = query.filter(Email.mailbox_account_id.in_(user_mailbox_ids))
    
    if status != "all":
        # 'completed' in UI maps to 'parsed' or 'completed' in DB
        if status == "completed":
            query = query.filter(Email.processing_status.in_(["parsed", "completed"]))
        else:
            query = query.filter(Email.processing_status == status)
            
    if search:
        search_term = f"%{search}%"
        query = query.filter(or_(Email.sender_email.ilike(search_term), Email.subject.ilike(search_term)))
        
    total = query.count()
    emails = query.options(
        load_only(
            Email.id, Email.sender_email, Email.subject, Email.labels,
            Email.processing_status, Email.received_at, Email.last_processing_error,
            Email.retention_category, Email.has_attachments, 
            Email.provider_message_id, Email.provider_thread_id
        )
    ).order_by(Email.created_at.desc(), Email.received_at.desc().nulls_last()).offset(skip).limit(limit).all()
    
    email_ids = [e.id for e in emails]
    
    # Batch-load the most recent workflow execution per email
    executions = []
    if email_ids:
        executions = db.query(WorkflowExecution, Workflow.name).join(
            Workflow, WorkflowExecution.workflow_id == Workflow.id
        ).filter(
            WorkflowExecution.email_id.in_(email_ids)
        ).order_by(
            WorkflowExecution.email_id, WorkflowExecution.executed_at.desc()
        ).all()
        
    exec_map = {}
    for ex, wf_name in executions:
        if ex.email_id not in exec_map:
            exec_map[ex.email_id] = (ex, wf_name)
            
    # Map to schema
    result_data = []
    for e in emails:
        # Category logic
        category = "Uncategorized"
        if e.labels and isinstance(e.labels, list):
            custom_labels = [l for l in e.labels if l not in ['UNREAD', 'IMPORTANT', 'SENT', 'INBOX', 'STARRED', 'TRASH', 'SPAM']]
            if custom_labels:
                category = custom_labels[0]
        elif e.retention_category:
            category = e.retention_category

        item = EmailListItem.model_validate(e)
        item.category = category
        item.has_attachments = e.has_attachments
        
        if e.id in exec_map:
            ex, wf_name = exec_map[e.id]
            item.workflow_name = wf_name
            item.workflow_status = ex.status
            
            # Determine last action from logs
            if ex.execution_logs_json and isinstance(ex.execution_logs_json, list) and len(ex.execution_logs_json) > 0:
                last_log = ex.execution_logs_json[-1]
                item.last_action = last_log.get("action", "Completed")
            else:
                item.last_action = "No Action"
                
            # Naive processing duration: executed_at - received_at
            if e.received_at and ex.executed_at:
                item.processing_duration = (ex.executed_at - e.received_at).total_seconds()
        else:
            item.workflow_name = "Not Processed"
            item.last_action = "Skipped"

        result_data.append(item)
    
    return PaginatedEmailResponse(
        data=result_data,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit
    )


@router.get("/stats")
def get_email_stats(db: Session = Depends(get_db)):
    results = db.query(Email.processing_status, func.count(Email.id)).group_by(Email.processing_status).all()
    stats = {status: count for status, count in results}
    stats["total"] = sum(stats.values())
    return stats

@router.get("/export")
def export_emails(status: str = Query("all"), search: str = Query(""), db: Session = Depends(get_db)):
    query = db.query(Email)
    if status != "all":
        # 'completed' in UI maps to 'parsed' or 'completed' in DB
        if status == "completed":
            query = query.filter(Email.processing_status.in_(["parsed", "completed"]))
        else:
            query = query.filter(Email.processing_status == status)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter((Email.sender_email.ilike(search_term)) | (Email.subject.ilike(search_term)))
        
    emails = query.order_by(Email.received_at.desc()).all()
    
    # Audit log: tracking export action for compliance
    logger.info(f"AUDIT: User exported {len(emails)} emails. Status filter: {status}, Search: {search}")
    
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Emails Export"
    ws.append(["Recipient", "Subject", "Category", "Status", "Sent Time", "Body Content"])
    
    for e in emails:
        # Replicate UI category logic cleanly - from retention_category only
        category = e.retention_category if e.retention_category else "Uncategorized"
            
        ws.append([
            e.sender_email or 'Unknown Sender',
            e.subject or '(No Subject)',
            category,
            e.processing_status,
            str(e.received_at),
            e.body_text or e.snippet or ''
        ])
        
    wb.save(path)
    wb.close()
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"email-monitoring-export-{date_str}.xlsx"
    return FileResponse(path, filename=filename, background=BackgroundTask(os.remove, path))

@router.get("/{email_id}", response_model=EmailDetailResponse)
def get_email_detail(email_id: str, db: Session = Depends(get_db)):
    from fastapi import HTTPException
    
    # Pre-validate uuid format to avoid postgres DataError on invalid inputs
    import uuid
    try:
        uuid.UUID(email_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid email ID format")
        
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
        
    executions = db.query(WorkflowExecution, Workflow.name).join(
        Workflow, WorkflowExecution.workflow_id == Workflow.id
    ).filter(
        WorkflowExecution.email_id == email_id
    ).order_by(WorkflowExecution.executed_at.asc()).all()
    
    # Base category logic - ONLY from retention_category to avoid mixing with Gmail Labels
    category = email.retention_category if email.retention_category else "Uncategorized"

    # Convert to response
    detail = EmailDetailResponse.model_validate(email)
    detail.category = category
    detail.has_attachments = email.has_attachments
    
    # Attachments
    from app.models.attachment import Attachment
    attachments = db.query(Attachment).filter(Attachment.email_id == email_id).all()
    detail.attachments = [
        {"id": a.id, "filename": a.filename, "mime_type": a.mime_type, "size_bytes": a.size_bytes} 
        for a in attachments
    ]
    
    timeline = []
    # 1. Collected Event
    timeline.append({
        "timestamp": str(email.received_at),
        "title": "Email Collected",
        "description": f"Collected via Gmail API (ID: {email.provider_message_id})",
        "status": "success"
    })
    
    if not executions:
        detail.workflow_name = "Not Processed"
        detail.last_action = "Skipped"
    else:
        # Sort execution logs for timeline
        last_ex, wf_name = executions[-1]
        detail.workflow_name = wf_name
        detail.workflow_status = last_ex.status
        
        # Build timeline from all executions
        for ex, w_name in executions:
            timeline.append({
                "timestamp": str(ex.executed_at),
                "title": f"Workflow Matched: {w_name}",
                "description": f"Execution started with status {ex.status}",
                "status": "info"
            })
            if ex.execution_logs_json and isinstance(ex.execution_logs_json, list):
                for log in ex.execution_logs_json:
                    timeline.append({
                        "timestamp": log.get("timestamp", str(ex.executed_at)),
                        "title": log.get("action", "Action Executed"),
                        "description": log.get("message", "No message"),
                        "status": "success" if log.get("level") != "ERROR" else "error"
                    })
        
        # Last Action
        if last_ex.execution_logs_json and isinstance(last_ex.execution_logs_json, list) and len(last_ex.execution_logs_json) > 0:
            detail.last_action = last_ex.execution_logs_json[-1].get("action", "Completed")
        else:
            detail.last_action = "No Action"
            
        if email.received_at and last_ex.executed_at:
            detail.processing_duration = (last_ex.executed_at - email.received_at).total_seconds()
            
    detail.execution_timeline = timeline
    return detail


@router.post("/{email_id}/classify")
def classify_email(email_id: str, db: Session = Depends(get_db)):
    try:
        import uuid
        uuid.UUID(email_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid email ID format")

    try:
        from app.services.category_matcher_service import CategoryMatcherService
        svc = CategoryMatcherService(db)
        result = svc.classify(email_id)
        if not result:
            raise HTTPException(status_code=404, detail="Email not found or classification failed")
        return success_response(data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{email_id}/send")
def send_email_reply(email_id: str, db: Session = Depends(get_db)):
    try:
        import uuid
        uuid.UUID(email_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid email ID format")

    try:
        from app.models.ai_approval import AIApproval
        approval = db.query(AIApproval).filter(
            AIApproval.email_id == email_id,
            AIApproval.status == "approved"
        ).order_by(AIApproval.created_at.desc()).first()

        if not approval:
            raise HTTPException(status_code=404, detail="No approved draft found for this email")

        from app.services.email_sender_service import EmailSenderService
        svc = EmailSenderService(db)
        result = svc.send_reply(str(approval.id))
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error", "Send failed"))
        return success_response(data=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
