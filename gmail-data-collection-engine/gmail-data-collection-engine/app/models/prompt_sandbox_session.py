from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class PromptSandboxSession(Base):
    __tablename__ = "prompt_sandbox_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    template_id = Column(UUID(as_uuid=True), ForeignKey("business_prompt_templates.id", ondelete="SET NULL"), nullable=True)
    template_version = Column(Integer, nullable=True)
    variable_values = Column(JSONB, nullable=False, server_default=text("'{}'"))
    variables_snapshot = Column(JSONB, nullable=True)
    company_settings_snapshot = Column(JSONB, nullable=True)
    provider_snapshot = Column(JSONB, nullable=True)
    rendered_prompt = Column(Text, nullable=True)
    validation_result = Column(JSONB, nullable=True)
    variables_used = Column(JSONB, nullable=True)
    variables_missing = Column(JSONB, nullable=True)
    variables_unknown = Column(JSONB, nullable=True)
    prompt_length_chars = Column(Integer, nullable=True)
    estimated_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Float, nullable=True)
    warnings = Column(JSONB, nullable=True, server_default=text("'[]'"))
    status = Column(String(30), nullable=False, server_default=text("'pending'"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    template = relationship("BusinessPromptTemplate", foreign_keys=[template_id])
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index('ix_pss_template', 'template_id'),
        Index('ix_pss_created_by', 'created_by'),
    )
