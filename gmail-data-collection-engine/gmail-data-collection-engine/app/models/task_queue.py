from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base

class TaskQueue(Base):
    __tablename__ = "task_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    queue_name = Column(String(50), nullable=False)
    task_type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    payload = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    status = Column(String(20), nullable=False, server_default=text("'pending'"))
    priority = Column(Integer, nullable=False, server_default=text("5"))
    retry_count = Column(Integer, nullable=False, server_default=text("0"))
    max_retries = Column(Integer, nullable=False, server_default=text("3"))
    scheduled_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        Index('ix_tq_status_priority', 'status', 'priority', postgresql_using='btree'),
        Index('ix_tq_queue_name', 'queue_name', 'status'),
        Index('ix_tq_entity', 'entity_type', 'entity_id'),
    )
