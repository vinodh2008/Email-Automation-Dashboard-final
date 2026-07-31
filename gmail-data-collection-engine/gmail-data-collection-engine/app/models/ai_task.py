from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, ForeignKey, Index, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class AITask(Base):
    __tablename__ = "ai_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    business_category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(String(30), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    prompt_template_id = Column(UUID(as_uuid=True), ForeignKey("business_prompt_templates.id", ondelete="SET NULL"), nullable=True)
    model_override = Column(String(150), nullable=True)
    temperature_override = Column(Float, nullable=True)
    max_tokens_override = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, nullable=False, server_default=text("true"))
    execution_order = Column(Integer, nullable=False, server_default=text("0"))
    config = Column(JSONB, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    category = relationship("BusinessCategory", primaryjoin="AITask.business_category_id == BusinessCategory.id", backref="ai_tasks")

    __table_args__ = (
        UniqueConstraint('business_category_id', 'task_type', name='uq_ai_task_category_type'),
        Index('ix_at_category', 'business_category_id'),
    )
