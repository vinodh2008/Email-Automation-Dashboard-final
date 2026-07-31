from sqlalchemy import Column, String, DateTime, Float, Integer, Text, text, Index, CheckConstraint, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class Email(Base):
    __tablename__ = "emails"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    mailbox_account_id = Column(UUID(as_uuid=True), ForeignKey("mailbox_accounts.id", ondelete="RESTRICT"), nullable=False)
    provider_message_id = Column(String, nullable=False)
    provider_thread_id = Column(String, nullable=True)
    sender_email = Column(String, nullable=True)
    to_recipients = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    cc_recipients = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    bcc_recipients = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    subject = Column(String, nullable=True)
    body_text = Column(String, nullable=True)
    body_html = Column(String, nullable=True)
    snippet = Column(String, nullable=True)
    labels = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    received_at = Column(DateTime(timezone=True), nullable=True)
    is_read = Column(Boolean, nullable=False, server_default=text("false"))
    has_attachments = Column(Boolean, nullable=False, server_default=text("false"))
    raw_email_json = Column(JSONB, nullable=True)

    processing_status = Column(String, nullable=False, server_default="collected")
    last_processing_error = Column(String, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    ai_processing_status = Column(String, nullable=False, server_default="not_started")
    ai_processed_at = Column(DateTime(timezone=True), nullable=True)

    record_status = Column(String, nullable=False, server_default="active")
    archived_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    retention_category = Column(String, nullable=True)

    business_category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories.id", ondelete="SET NULL"), nullable=True)
    classification_confidence = Column(Float, nullable=True)
    ai_draft_status = Column(String(20), server_default=text("'none'"))
    ai_draft_content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    extracted_entities = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    mailbox_account = relationship("MailboxAccount", back_populates="emails")
    attachments = relationship("Attachment", back_populates="email", passive_deletes=True)

    __table_args__ = (
        Index('uq_email_account_provider_msg_id', 'mailbox_account_id', 'provider_message_id', unique=True),
        Index('ix_email_account_received_at', 'mailbox_account_id', text('received_at DESC')),
        Index('ix_email_account_thread_id', 'mailbox_account_id', 'provider_thread_id'),
        Index('ix_email_account_processing_status', 'mailbox_account_id', 'processing_status'),
        Index('ix_email_account_record_status', 'mailbox_account_id', 'record_status'),
        CheckConstraint("processing_status IN ('collected', 'parsed', 'completed', 'failed')", name="ck_email_processing_status"),
        CheckConstraint("ai_processing_status IN ('not_started', 'pending', 'completed', 'failed')", name="ck_email_ai_processing_status"),
        CheckConstraint("record_status IN ('active', 'archived', 'deleted')", name="ck_email_record_status"),
    )
