from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class AITaskExecution(Base):
    __tablename__ = "ai_task_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    ai_task_id = Column(UUID(as_uuid=True), ForeignKey("ai_tasks.id", ondelete="CASCADE"), nullable=False)
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, server_default=text("'pending'"))
    input_payload = Column(JSONB, nullable=True)
    output_payload = Column(JSONB, nullable=True)
    model_used = Column(String(150), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    ai_task = relationship("AITask", backref="executions")
    email = relationship("Email", backref="ai_task_executions")

    __table_args__ = (
        Index('ix_ate_ai_task', 'ai_task_id'),
        Index('ix_ate_email', 'email_id'),
        Index('ix_ate_status', 'status'),
    )
