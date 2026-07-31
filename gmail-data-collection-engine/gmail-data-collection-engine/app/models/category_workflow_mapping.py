from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Index, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class CategoryWorkflowMapping(Base):
    __tablename__ = "category_workflow_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    business_category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories.id", ondelete="CASCADE"), nullable=False)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False)
    priority = Column(Integer, nullable=False, server_default=text("0"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    category = relationship("BusinessCategory", foreign_keys=[business_category_id], backref="workflow_mappings")
    workflow = relationship("Workflow", foreign_keys=[workflow_id])
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        UniqueConstraint('business_category_id', 'workflow_id', name='uq_category_workflow'),
        Index('ix_cwm_category', 'business_category_id'),
        Index('ix_cwm_workflow', 'workflow_id'),
    )
