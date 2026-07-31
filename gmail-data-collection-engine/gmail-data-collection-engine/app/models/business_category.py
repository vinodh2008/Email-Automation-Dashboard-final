from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, ForeignKey, Index, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class BusinessCategory(Base):
    __tablename__ = "business_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(150), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    priority = Column(Integer, nullable=False, server_default=text("0"))
    display_order = Column(Integer, nullable=False, server_default=text("0"))
    color = Column(String(7), nullable=True, server_default=text("'#6366F1'"))
    icon = Column(String(50), nullable=True)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(30), nullable=False, server_default=text("'active'"))
    default_prompt_template_id = Column(UUID(as_uuid=True), nullable=True)
    default_workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    is_default = Column(Boolean, nullable=False, server_default=text("false"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    # AI Configuration Override (NULL = inherit global)
    ai_model = Column(String(150), nullable=True)
    ai_temperature = Column(Float, nullable=True)
    ai_max_tokens = Column(Integer, nullable=True)
    ai_timeout = Column(Integer, nullable=True)
    ai_retry_count = Column(Integer, nullable=True)

    # Category Metrics
    emails_processed = Column(Integer, nullable=False, server_default=text("0"))
    drafts_generated = Column(Integer, nullable=False, server_default=text("0"))
    approval_rate = Column(Float, nullable=True)
    avg_generation_time_ms = Column(Integer, nullable=True)
    avg_tokens_used = Column(Integer, nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    # Reserved for Future Phases
    matching_strategy = Column(String(50), nullable=True)
    confidence_threshold = Column(Float, nullable=True)
    knowledge_source_id = Column(UUID(as_uuid=True), nullable=True)
    validation_policy_id = Column(UUID(as_uuid=True), nullable=True)
    rule_set_id = Column(UUID(as_uuid=True), nullable=True)
    decision_engine_id = Column(UUID(as_uuid=True), nullable=True)
    approval_flow_id = Column(UUID(as_uuid=True), nullable=True)

    owner = relationship("User", foreign_keys=[owner_user_id])
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])

    __table_args__ = (
        Index('ix_business_categories_code', 'code'),
        Index('ix_business_categories_priority', 'priority'),
        Index('ix_business_categories_display_order', 'display_order'),
        Index('ix_business_categories_status', 'status'),
        Index('ix_business_categories_is_default', 'is_default', postgresql_where=text("is_default = true")),
    )
