from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class EmailSend(Base):
    __tablename__ = "email_sends"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    ai_approval_id = Column(UUID(as_uuid=True), ForeignKey("ai_approvals.id", ondelete="SET NULL"), nullable=True)
    gmail_message_id = Column(String(100), nullable=True)
    thread_id = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, server_default=text("'pending'"))
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    email = relationship("Email", backref="sends")

    __table_args__ = (
        Index('ix_es_email', 'email_id'),
    )
