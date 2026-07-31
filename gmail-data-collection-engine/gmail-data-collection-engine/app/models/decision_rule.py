from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class DecisionRule(Base):
    __tablename__ = "decision_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    business_category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories(id)", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, nullable=False, server_default=text("true"))
    priority = Column(Integer, nullable=False, server_default=text("0"))
    min_confidence = Column(Float, server_default=text("0.9"))
    max_risk_level = Column(String(20), server_default=text("'low'"))
    max_email_value = Column(Float, nullable=True)
    sender_whitelist = Column(JSONB, server_default=text("'[]'::jsonb"))
    category_codes = Column(JSONB, server_default=text("'[]'::jsonb"))
    action = Column(String(30), nullable=False, server_default=text("'escalate'"))
    approval_chain = Column(JSONB, server_default=text("'[]'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    category = relationship("BusinessCategory", backref="decision_rules")

    __table_args__ = (
        Index('ix_dr_category', 'business_category_id'),
    )
