from sqlalchemy import Column, String, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.session import Base
from app.models.base import TimestampMixin


class LeadEvent(TimestampMixin, Base):
    __tablename__ = "lead_events"

    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_metadata = Column("metadata", JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
