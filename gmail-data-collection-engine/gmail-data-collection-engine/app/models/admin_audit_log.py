from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    user = relationship("User")

    __table_args__ = (
        Index('ix_admin_audit_log_user_id', 'user_id'),
        Index('ix_admin_audit_log_created_at', 'created_at', postgresql_using='btree', postgresql_ops={'created_at': 'DESC'}),
        Index('ix_admin_audit_log_entity_type', 'entity_type'),
    )
