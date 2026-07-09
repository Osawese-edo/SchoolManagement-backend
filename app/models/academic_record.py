from sqlalchemy import Column, ForeignKey, Float, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from app.models.base import TimestampMixin
from datetime import datetime, timezone


class AcademicRecord(TimestampMixin, Base):
    __tablename__ = "academic_records"

    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_subject_id = Column(UUID(as_uuid=True), ForeignKey("class_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    term_id = Column(UUID(as_uuid=True), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    max_score = Column(Float, default=100.0, nullable=False)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    teacher_comment = Column(Text, nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint('student_id', 'class_subject_id', 'term_id', name='uq_academic_record_composite'),
    )
