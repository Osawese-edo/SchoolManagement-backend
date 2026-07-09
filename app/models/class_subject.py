from sqlalchemy import Column, ForeignKey, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import TimestampMixin


class ClassSubject(TimestampMixin, Base):
    __tablename__ = "class_subjects"

    class_id = Column(UUID(as_uuid=True), ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("staff.id", ondelete="SET NULL"), nullable=True, index=True)
    max_score = Column(Float, default=100.0, nullable=False)

    class_rel = relationship("SchoolClass", foreign_keys=[class_id])
    subject_rel = relationship("Subject", foreign_keys=[subject_id])
    teacher_rel = relationship("Staff", foreign_keys=[teacher_id])
    assessment_configs = relationship("AssessmentConfig", back_populates="class_subject_rel", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('class_id', 'subject_id', name='uq_class_subject_composite'),
    )
