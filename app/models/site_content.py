from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from app.models.base import TimestampMixin


class SiteContent(TimestampMixin, Base):
    __tablename__ = "site_content"

    section = Column(String(50), nullable=False, index=True)
    field_key = Column(String(100), nullable=False)
    field_value = Column(Text, nullable=True)
    content_type = Column(String(20), nullable=False, default="text")
    is_active = Column(Boolean, default=True, nullable=False)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
