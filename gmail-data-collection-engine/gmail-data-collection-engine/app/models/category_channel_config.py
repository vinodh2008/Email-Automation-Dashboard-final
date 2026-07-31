from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index, text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class CategoryChannelConfig(Base):
    __tablename__ = "category_channel_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    business_category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories(id)", ondelete="CASCADE"), nullable=False)
    channel = Column(String(30), nullable=False)
    is_enabled = Column(Boolean, nullable=False, server_default=text("false"))
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows(id)", ondelete="SET NULL"), nullable=True)
    prompt_template_id = Column(UUID(as_uuid=True), ForeignKey("business_prompt_templates(id)", ondelete="SET NULL"), nullable=True)
    channel_config = Column(JSONB, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    category = relationship("BusinessCategory", backref="channel_configs")

    __table_args__ = (
        UniqueConstraint('business_category_id', 'channel', name='uq_category_channel'),
        Index('ix_ccc_category', 'business_category_id'),
        Index('ix_ccc_channel', 'channel'),
    )
