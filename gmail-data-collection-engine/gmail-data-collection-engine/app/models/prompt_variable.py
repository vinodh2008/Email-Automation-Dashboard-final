from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class PromptVariable(Base):
    __tablename__ = "prompt_variables"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    data_type = Column(String(30), nullable=False, server_default=text("'STRING'"))
    scope = Column(String(30), nullable=False, server_default=text("'GLOBAL'"))
    source_adapter = Column(String(50), nullable=False, server_default=text("'STATIC'"))
    source_config = Column(JSONB, nullable=True)
    default_value = Column(Text, nullable=True)
    is_required = Column(Boolean, nullable=False, server_default=text("false"))
    validation_regex = Column(Text, nullable=True)
    sample_value = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, server_default=text("'email'"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index('ix_pv_name', 'name', unique=True),
        Index('ix_pv_scope', 'scope'),
        Index('ix_pv_source_adapter', 'source_adapter'),
        Index('ix_pv_category', 'category'),
    )
