from sqlalchemy import Column, Boolean, DateTime, Integer, ForeignKey, Index, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class CategoryAITaskMapping(Base):
    __tablename__ = "category_ai_task_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    business_category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories.id", ondelete="CASCADE"), nullable=False)
    ai_task_id = Column(UUID(as_uuid=True), ForeignKey("ai_tasks.id", ondelete="CASCADE"), nullable=False)
    task_order = Column(Integer, nullable=False, server_default=text("0"))
    is_enabled = Column(Boolean, nullable=False, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    category = relationship("BusinessCategory", backref="ai_task_mappings")
    ai_task = relationship("AITask", backref="category_mappings")

    __table_args__ = (
        UniqueConstraint('business_category_id', 'ai_task_id', name='uq_category_ai_task'),
        Index('ix_cam_category', 'business_category_id'),
        Index('ix_cam_ai_task', 'ai_task_id'),
    )
