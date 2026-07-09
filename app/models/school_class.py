from sqlalchemy import Column, String, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import TimestampMixin


class SchoolClass(TimestampMixin, Base):
    __tablename__ = "school_classes"

    name = Column(String(100), nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("staff.id"), nullable=True)
    academic_term_id = Column(UUID(as_uuid=True), ForeignKey("academic_terms.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    teacher_rel = relationship("Staff", foreign_keys=[teacher_id])
    term_rel = relationship("AcademicTerm", foreign_keys=[academic_term_id])
