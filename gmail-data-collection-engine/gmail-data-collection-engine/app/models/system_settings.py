from sqlalchemy import Column, String, DateTime, Text, ForeignKey, text
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(100), primary_key=True)
    value_json = Column(JSONB, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, server_default=text("'general'"))
    updated_by = Column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
