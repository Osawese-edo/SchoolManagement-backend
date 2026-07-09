from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from app.models.base import TimestampMixin
from datetime import datetime


class Testimonial(TimestampMixin, Base):
    __tablename__ = "testimonials"

    customer_name = Column(String(100), nullable=False)
    rating = Column(Integer, nullable=False)
    review_text = Column(Text, nullable=False)
    is_published = Column(Boolean, default=False, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    admin_reply = Column(Text, nullable=True)
    replied_at = Column(DateTime, nullable=True)
    replied_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
