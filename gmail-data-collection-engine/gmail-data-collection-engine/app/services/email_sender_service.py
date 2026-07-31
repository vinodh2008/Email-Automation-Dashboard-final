"""
EmailSenderService — Send approved email replies via Gmail API.
Phase 2B: Integrates with Gmail OAuth provider for email sending.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

logger = logging.getLogger("email_sender_service")


class EmailSenderService:
    def __init__(self, db: Session):
        self.db = db

    def send_reply(self, approval_id: str) -> Dict[str, Any]:
        """Send an approved email reply via Gmail API."""
        try:
            from app.models.ai_approval import AIApproval
            from app.models.email import Email
            from app.models.email_send import EmailSend
            from app.models.mailbox_account import MailboxAccount
            import uuid
            
            approval = self.db.query(AIApproval).filter(AIApproval.id == approval_id).first()
            if not approval:
                return {"status": "error", "error": "Approval not found"}
            
            email = self.db.query(Email).filter(Email.id == approval.email_id).first()
            if not email:
                return {"status": "error", "error": "Original email not found"}
            
            account = self.db.query(MailboxAccount).filter(
                MailboxAccount.id == email.mailbox_account_id
            ).first()
            
            send_record = EmailSend(
                email_id=email.id,
                ai_approval_id=approval.id,
                status="pending",
            )
            self.db.add(send_record)
            self.db.flush()
            
            try:
                from app.providers.gmail_provider import GmailProvider
                provider = GmailProvider()
                provider.authenticate(interactive=False)
                
                reply_content = approval.edited_content or approval.generated_content
                to_address = email.sender_email
                subject = f"Re: {email.subject}" if email.subject else "Re: Your inquiry"
                thread_id = email.provider_thread_id if hasattr(email, 'provider_thread_id') else None
                
                result = provider.send_message(
                    to=to_address,
                    subject=subject,
                    body=reply_content,
                    thread_id=thread_id,
                )
                
                send_record.status = "sent"
                send_record.sent_at = datetime.now(timezone.utc)
                send_record.gmail_message_id = result.get("id")
                send_record.thread_id = result.get("threadId")
                
                email.ai_draft_status = "sent"
                
                self.db.commit()
                
                logger.info(f"[EMAIL_SEND] Reply sent for approval {approval_id}")
                return {
                    "status": "sent",
                    "send_id": str(send_record.id),
                    "gmail_message_id": send_record.gmail_message_id,
                }
                
            except Exception as gmail_err:
                send_record.status = "failed"
                send_record.error_message = str(gmail_err)
                self.db.commit()
                logger.error(f"[EMAIL_SEND] Gmail API error: {gmail_err}")
                return {"status": "failed", "error": str(gmail_err)}
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"[EMAIL_SEND] Failed to send reply for approval {approval_id}: {e}")
            return {"status": "error", "error": str(e)}

    def send_batch(self, approval_ids: List[str]) -> List[Dict[str, Any]]:
        """Send multiple approved replies."""
        results = []
        for approval_id in approval_ids:
            result = self.send_reply(approval_id)
            results.append(result)
        return results

    def retry_send(self, send_id: str) -> Dict[str, Any]:
        """Retry a failed send."""
        try:
            from app.models.email_send import EmailSend
            send_record = self.db.query(EmailSend).filter(EmailSend.id == send_id).first()
            if not send_record or send_record.status != "failed":
                return {"status": "error", "error": "Send record not found or not failed"}
            
            return self.send_reply(str(send_record.ai_approval_id))
        except Exception as e:
            logger.error(f"[EMAIL_SEND] Failed to retry send {send_id}: {e}")
            return {"status": "error", "error": str(e)}

    def get_send_history(self, email_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get send history."""
        try:
            from app.models.email_send import EmailSend
            query = self.db.query(EmailSend)
            if email_id:
                query = query.filter(EmailSend.email_id == email_id)
            sends = query.order_by(EmailSend.created_at.desc()).limit(limit).all()
            
            return [{
                "id": str(s.id),
                "email_id": str(s.email_id),
                "ai_approval_id": str(s.ai_approval_id) if s.ai_approval_id else None,
                "gmail_message_id": s.gmail_message_id,
                "thread_id": s.thread_id,
                "status": s.status,
                "sent_at": s.sent_at.isoformat() if s.sent_at else None,
                "error_message": s.error_message,
                "retry_count": s.retry_count,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            } for s in sends]
        except Exception as e:
            logger.error(f"[EMAIL_SEND] Failed to get send history: {e}")
            return []