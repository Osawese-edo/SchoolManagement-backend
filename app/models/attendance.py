from sqlalchemy import Column, ForeignKey, Date, String, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from app.models.base import TimestampMixin
from datetime import datetime, timezone


class Attendance(TimestampMixin, Base):
    __tablename__ = "attendance"

    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(UUID(as_uuid=True), ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    status = Column(String(10), nullable=False)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint('student_id', 'class_id', 'date', name='uq_attendance_student_class_date'),
    )
