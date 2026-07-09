from sqlalchemy import Column, ForeignKey, Float, DateTime, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from app.models.base import TimestampMixin
from datetime import datetime, timezone


class AssessmentScore(TimestampMixin, Base):
    __tablename__ = "assessment_scores"

    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    class_subject_id = Column(UUID(as_uuid=True), ForeignKey("class_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    term_id = Column(UUID(as_uuid=True), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_config_id = Column(UUID(as_uuid=True), ForeignKey("assessment_configs.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    teacher_comment = Column(Text, nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "class_subject_id", "term_id", "assessment_config_id", name="uq_assessment_score_composite"),
    )
