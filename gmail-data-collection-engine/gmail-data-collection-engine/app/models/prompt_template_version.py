from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Index, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class PromptTemplateVersion(Base):
    __tablename__ = "prompt_template_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    base_template_id = Column(UUID(as_uuid=True), ForeignKey("business_prompt_templates.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    name = Column(String(150), nullable=False)
    purpose = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    prompt_content = Column(Text, nullable=False)
    variables_json = Column(Text, nullable=True, server_default=text("'[]'"))
    status = Column(String(30), nullable=False, server_default=text("'draft'"))
    change_summary = Column(Text, nullable=True)
    sandbox_result = Column(JSONB, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    published_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    archived_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rollback_from_version = Column(Integer, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    template = relationship("BusinessPromptTemplate", foreign_keys=[base_template_id], backref="versions")
    creator = relationship("User", foreign_keys=[created_by])
    publisher = relationship("User", foreign_keys=[published_by])
    archiver = relationship("User", foreign_keys=[archived_by])

    __table_args__ = (
        UniqueConstraint('base_template_id', 'version_number', name='uq_template_version'),
        Index('ix_ptv_base_template', 'base_template_id'),
    )
