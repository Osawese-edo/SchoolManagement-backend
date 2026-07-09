from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from app.models.base import TimestampMixin
import uuid


class GradingScale(TimestampMixin, Base):
    __tablename__ = "grading_scales"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grade = Column(String(5), nullable=False)
    min_score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    remark = Column(String(100), default="")
    is_active = Column(Boolean, default=True)
