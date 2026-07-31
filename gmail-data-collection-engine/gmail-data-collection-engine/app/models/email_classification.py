from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class EmailClassification(Base):
    __tablename__ = "email_classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email_id = Column(UUID(as_uuid=True), ForeignKey("emails(id)", ondelete="CASCADE"), nullable=False)
    business_category_id = Column(UUID(as_uuid=True), ForeignKey("business_categories(id)", ondelete="SET NULL"), nullable=True)
    confidence = Column(Float, nullable=False)
    matching_method = Column(String(30), nullable=False)
    matching_details = Column(JSONB, server_default=text("'{}'::jsonb"))
    classified_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    classified_by = Column(String(30), nullable=False, server_default=text("'system'"))

    email = relationship("Email", backref="classifications")

    __table_args__ = (
        Index('ix_ec_email', 'email_id'),
        Index('ix_ec_category', 'business_category_id'),
    )
