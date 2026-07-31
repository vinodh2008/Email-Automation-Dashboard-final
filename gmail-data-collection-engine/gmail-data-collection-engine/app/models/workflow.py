from sqlalchemy import Column, String, Boolean, DateTime, text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    mailbox_account_id = Column(UUID(as_uuid=True), ForeignKey("mailbox_accounts.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(String, nullable=True)
    trigger_conditions_json = Column(JSONB, nullable=False)
    actions_json = Column(JSONB, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    business_category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    mailbox_account = relationship("MailboxAccount")
    executions = relationship("WorkflowExecution", back_populates="workflow", passive_deletes=True)

    __table_args__ = (
        Index('ix_workflows_mailbox_id', 'mailbox_account_id'),
    )

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), nullable=False)
    execution_logs_json = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    executed_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    workflow = relationship("Workflow", back_populates="executions")
    email = relationship("Email")

    __table_args__ = (
        Index('ix_workflow_executions_workflow_id', 'workflow_id'),
        Index('ix_workflow_executions_email_id', 'email_id'),
    )
