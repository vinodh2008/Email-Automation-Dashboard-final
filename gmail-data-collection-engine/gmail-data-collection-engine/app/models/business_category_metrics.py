from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class BusinessCategoryMetrics(Base):
    __tablename__ = "business_category_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    business_category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories.id", ondelete="CASCADE"), nullable=False, unique=True)
    emails_processed = Column(Integer, nullable=False, server_default=text("0"))
    drafts_generated = Column(Integer, nullable=False, server_default=text("0"))
    approval_rate = Column(Float, nullable=True)
    avg_generation_time_ms = Column(Integer, nullable=True)
    avg_tokens_used = Column(Integer, nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    category = relationship("BusinessCategory", foreign_keys=[business_category_id])
