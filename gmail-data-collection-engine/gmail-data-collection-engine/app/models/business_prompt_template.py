from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class BusinessPromptTemplate(Base):
    __tablename__ = "business_prompt_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    business_category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(150), nullable=False)
    purpose = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    prompt_content = Column(Text, nullable=False)
    variables_json = Column(Text, nullable=True, server_default=text("'[]'"))
    current_version = Column(Integer, nullable=False, server_default=text("1"))
    published_version = Column(Integer, nullable=True)
    testing_status = Column(String(30), nullable=False, server_default=text("'untested'"))
    status = Column(String(30), nullable=False, server_default=text("'draft'"))
    usage_count = Column(Integer, nullable=False, server_default=text("0"))
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    category = relationship("BusinessCategory", foreign_keys=[business_category_id])
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])

    __table_args__ = (
        Index('ix_bpt_category', 'business_category_id'),
        Index('ix_bpt_status', 'status'),
    )
