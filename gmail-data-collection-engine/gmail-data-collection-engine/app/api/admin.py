from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Optional

from app.db.session import get_db
from app.models import MailboxAccount, Email, Attachment, SyncRun, SyncLog, SyncError
from app.schemas.admin import (
    DashboardSummaryResponse,
    MailboxAdminResponse,
    EmailAdminListResponse,
    EmailAdminDetailResponse,
    AttachmentAdminResponse,
    DownloadUrlResponse,
    SyncRunAdminResponse,
    SyncLogAdminResponse,
    SyncErrorAdminResponse,
    AttachmentMinimalResponse
)
from app.clients.supabase_client import get_supabase_client
from app.scheduler.scheduler_service import scheduler_service
from app.auth.dependencies import get_current_user

admin_router = APIRouter(
    prefix="/admin",
    tags=["Admin Dashboard"],
    dependencies=[Depends(get_current_user)]
)

@admin_router.get(
    "/dashboard/summary",
    response_model=DashboardSummaryResponse,
    summary="Dashboard Summary",
    description="Returns overall Gmail engine statistics for the admin dashboard."
)
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_mailboxes = db.query(func.count(MailboxAccount.id)).scalar() or 0
    total_emails = db.query(func.count(Email.id)).scalar() or 0
    total_attachments = db.query(func.count(Attachment.id)).scalar() or 0
    total_sync_runs = db.query(func.count(SyncRun.id)).scalar() or 0
    
    successful_syncs = db.query(func.count(SyncRun.id)).filter(SyncRun.status == "completed").scalar() or 0
    failed_syncs = db.query(func.count(SyncRun.id)).filter(SyncRun.status.in_(["failed", "partial_failure"])).scalar() or 0
    
    last_sync = db.query(func.max(SyncRun.started_at)).scalar()
    
    sched_status = scheduler_service.get_status()
    status_str = "running" if sched_status["is_running"] else "stopped"
    
    return DashboardSummaryResponse(
        total_mailboxes=total_mailboxes,
        total_emails=total_emails,
        total_attachments=total_attachments,
        total_sync_runs=total_sync_runs,
        successful_syncs=successful_syncs,
        failed_syncs=failed_syncs,
        last_sync_time=last_sync,
        scheduler_status=status_str
    )

@admin_router.get(
    "/mailboxes",
    response_model=List[MailboxAdminResponse],
    summary="List Mailboxes",
    description="Returns a list of all connected mailbox accounts."
)
def get_mailboxes(db: Session = Depends(get_db)):
    mailboxes = db.query(MailboxAccount).order_by(desc(MailboxAccount.created_at)).all()
    return [
        MailboxAdminResponse(
            id=m.id,
            email_address=m.account_identifier,
            sync_mode=m.sync_status,
            history_id=m.last_history_id,
            last_sync_at=m.last_sync_at,
            created_at=m.created_at
        )
        for m in mailboxes
    ]

@admin_router.get(
    "/emails",
    response_model=List[EmailAdminListResponse],
    summary="List Emails",
    description="Returns a paginated list of synced emails with optional search filters."
)
def list_emails(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    subject: Optional[str] = None,
    sender: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Email)
    
    if subject:
        query = query.filter(Email.subject.ilike(f"%{subject}%"))
    if sender:
        query = query.filter(Email.sender_email.ilike(f"%{sender}%"))
        
    emails = query.order_by(Email.received_at.desc().nulls_last()).offset(skip).limit(limit).all()
    
    return [
        EmailAdminListResponse(
            id=e.id,
            sender_email=e.sender_email,
            to_recipients=e.to_recipients,
            subject=e.subject,
            labels=e.labels,
            received_at=e.received_at,
            has_attachments=e.has_attachments
        )
        for e in emails
    ]

@admin_router.get(
    "/emails/{email_id}",
    response_model=EmailAdminDetailResponse,
    summary="Get Email Details",
    description="Returns full details of a specific email, including a snippet preview and related attachments."
)
def get_email_details(email_id: str, db: Session = Depends(get_db)):
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
        
    attachments = db.query(Attachment).filter(Attachment.email_id == email.id).all()
    
    return EmailAdminDetailResponse(
        id=email.id,
        sender_email=email.sender_email,
        to_recipients=email.to_recipients,
        subject=email.subject,
        labels=email.labels,
        received_at=email.received_at,
        has_attachments=email.has_attachments,
        body_preview=email.snippet or email.body_text[:200] if email.body_text else None,
        thread_id=email.provider_thread_id,
        related_attachments=[
            AttachmentMinimalResponse(
                id=a.id,
                file_name=a.file_name,
                mime_type=a.mime_type,
                size_bytes=a.size_bytes
            ) for a in attachments
        ]
    )

@admin_router.get(
    "/attachments",
    response_model=List[AttachmentAdminResponse],
    summary="List Attachments",
    description="Returns a paginated list of all synced attachments with parent email data."
)
def list_attachments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    attachments = db.query(Attachment).join(Email).order_by(desc(Attachment.created_at)).offset(skip).limit(limit).all()
    
    return [
        AttachmentAdminResponse(
            id=a.id,
            file_name=a.file_name,
            mime_type=a.mime_type,
            size_bytes=a.size_bytes,
            parent_email_subject=a.email.subject if a.email else None,
            sender_email=a.email.sender_email if a.email else None,
            storage_path=a.storage_path,
            created_at=a.created_at
        )
        for a in attachments
    ]

@admin_router.get(
    "/attachments/{attachment_id}",
    response_model=AttachmentAdminResponse,
    summary="Get Attachment",
    description="Returns full metadata for a specific attachment."
)
def get_attachment(attachment_id: str, db: Session = Depends(get_db)):
    a = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Attachment not found")
        
    return AttachmentAdminResponse(
        id=a.id,
        file_name=a.file_name,
        mime_type=a.mime_type,
        size_bytes=a.size_bytes,
        parent_email_subject=a.email.subject if a.email else None,
        sender_email=a.email.sender_email if a.email else None,
        storage_path=a.storage_path,
        created_at=a.created_at
    )

@admin_router.get(
    "/attachments/{attachment_id}/download-url",
    response_model=DownloadUrlResponse,
    summary="Generate Download URL",
    description="Generates a temporary signed URL from Supabase Storage for downloading an attachment."
)
def get_attachment_download_url(attachment_id: str, db: Session = Depends(get_db)):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment or not attachment.storage_path or not attachment.storage_bucket:
        raise HTTPException(status_code=404, detail="Attachment or storage path not found")
        
    client = get_supabase_client()
    try:
        # Create signed url valid for 60 seconds (1 minute)
        res = client.storage.from_(attachment.storage_bucket).create_signed_url(attachment.storage_path, 60)
        
        url = res.get('signedURL') if isinstance(res, dict) and 'signedURL' in res else res
        
        if not url:
            raise Exception("No URL returned from Supabase")
            
        return DownloadUrlResponse(url=url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate download url: {str(e)}")

@admin_router.get(
    "/sync-runs",
    response_model=List[SyncRunAdminResponse],
    summary="List Sync Runs",
    description="Returns a paginated list of recent sync runs."
)
def list_sync_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    runs = db.query(SyncRun).order_by(desc(SyncRun.started_at)).offset(skip).limit(limit).all()
    
    return [
        SyncRunAdminResponse(
            sync_run_id=r.id,
            sync_type=r.sync_type,
            status=r.status,
            emails_found=r.emails_found,
            emails_inserted=r.emails_inserted,
            duplicates_skipped=r.duplicates_skipped,
            emails_failed=r.emails_failed,
            attachments_uploaded=r.attachments_uploaded,
            started_at=r.started_at,
            completed_at=r.completed_at
        )
        for r in runs
    ]

@admin_router.get(
    "/sync-logs",
    response_model=List[SyncLogAdminResponse],
    summary="List Sync Logs",
    description="Returns a paginated list of recent synchronization logs."
)
def list_sync_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db)
):
    logs = db.query(SyncLog).order_by(desc(SyncLog.created_at)).offset(skip).limit(limit).all()
    
    return [
        SyncLogAdminResponse(
            id=l.id,
            level=l.level,
            message=l.message,
            metadata_json=l.metadata_json,
            created_at=l.created_at
        )
        for l in logs
    ]

@admin_router.get(
    "/sync-errors",
    response_model=List[SyncErrorAdminResponse],
    summary="List Sync Errors",
    description="Returns a paginated list of recorded synchronization errors."
)
def list_sync_errors(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    errors = db.query(SyncError).order_by(desc(SyncError.created_at)).offset(skip).limit(limit).all()
    
    return [
        SyncErrorAdminResponse(
            error_type=e.error_type,
            error_message=e.error_message,
            created_at=e.created_at,
            sync_run_id=e.sync_run_id
        )
        for e in errors
    ]
