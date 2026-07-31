from sqlalchemy import Column, String, Boolean, DateTime, Float, text, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class AIApproval(Base):
    __tablename__ = "ai_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    prompt_template_id = Column(UUID(as_uuid=True), ForeignKey("prompt_templates.id", ondelete="SET NULL"), nullable=True)
    generated_content = Column(Text, nullable=False)
    edited_content = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, server_default=text("'pending_review'"))  # pending_review, approved, rejected
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    auto_approved = Column(Boolean, server_default=text("false"))
    confidence_score = Column(Float, nullable=True)
    decision_rule_id = Column(UUID(as_uuid=True), ForeignKey("decision_rules(id)", ondelete="SET NULL"), nullable=True)
    knowledge_context_used = Column(JSONB, nullable=True)
    ai_task_id = Column(UUID(as_uuid=True), ForeignKey("ai_tasks(id)", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    workflow = relationship("Workflow")
    email = relationship("Email")
    prompt_template = relationship("PromptTemplate")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        Index('ix_ai_approvals_workflow_id', 'workflow_id'),
        Index('ix_ai_approvals_email_id', 'email_id'),
        Index('ix_ai_approvals_status', 'status'),
    )
