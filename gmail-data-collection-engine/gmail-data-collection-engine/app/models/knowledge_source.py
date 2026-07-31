from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    business_category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    source_type = Column(String(30), nullable=False)
    file_path = Column(Text, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    content_text = Column(Text, nullable=True)
    embedding_status = Column(String(20), server_default=text("'pending'"))
    embedding_model = Column(String(50), nullable=True)
    chunk_count = Column(Integer, server_default=text("0"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    category = relationship("BusinessCategory", backref="knowledge_sources")

    __table_args__ = (
        Index('ix_ks_category', 'business_category_id'),
    )
