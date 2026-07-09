from sqlalchemy import Column, ForeignKey, Float, String, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import TimestampMixin


class AssessmentConfig(TimestampMixin, Base):
    __tablename__ = "assessment_configs"

    class_subject_id = Column(UUID(as_uuid=True), ForeignKey("class_subjects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    max_score = Column(Float, nullable=False)
    sort_order = Column(Integer, default=0)
    is_exam = Column(Boolean, default=False)

    class_subject_rel = relationship("ClassSubject", foreign_keys=[class_subject_id], back_populates="assessment_configs")
