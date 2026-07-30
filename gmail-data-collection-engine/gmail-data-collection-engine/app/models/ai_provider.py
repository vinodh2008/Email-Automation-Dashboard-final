from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Float, text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class AIProvider(Base):
    __tablename__ = "ai_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(150), nullable=False)
    provider_type = Column(String(50), nullable=False)
    model = Column(String(150), nullable=True)
    default_model = Column(String(150), nullable=True)
    api_key_encrypted = Column(Text, nullable=True)
    api_key = Column(Text, nullable=True)
    base_url = Column(String(500), nullable=True)
    is_enabled = Column(Boolean, nullable=False, server_default=text("true"))
    is_primary = Column(Boolean, nullable=False, server_default=text("false"))
    priority = Column(Integer, nullable=False, server_default=text("0"))
    max_tokens = Column(Integer, nullable=True, server_default=text("800"))
    temperature = Column(Float, nullable=True, server_default=text("0.7"))
    status = Column(String(30), nullable=False, server_default=text("inactive"))
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    verified_model = Column(String(150), nullable=True)
    latency_ms = Column(Integer, nullable=True)
    timeout = Column(Integer, nullable=True, server_default=text("30"))
    retry_count = Column(Integer, nullable=True, server_default=text("3"))
    total_requests = Column(Integer, nullable=False, server_default=text("0"))
    successful_requests = Column(Integer, nullable=False, server_default=text("0"))
    failed_requests = Column(Integer, nullable=False, server_default=text("0"))
    total_tokens_used = Column(Integer, nullable=False, server_default=text("0"))
    avg_latency_ms = Column(Integer, nullable=True)
    health_score = Column(Float, nullable=True, server_default=text("100.0"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    user = relationship("User")

    __table_args__ = (
        Index('ix_ai_providers_user_id', 'user_id'),
        Index('ix_ai_providers_provider_type', 'provider_type'),
    )
