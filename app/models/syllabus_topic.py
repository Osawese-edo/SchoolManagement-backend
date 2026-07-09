from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, UUID as SQLUuid
from sqlalchemy.orm import relationship, backref
from uuid import uuid4

from app.db.session import Base
from app.models.base import TimestampMixin


class SyllabusTopic(TimestampMixin, Base):
    __tablename__ = "syllabus_topics"

    id = Column(SQLUuid, primary_key=True, default=uuid4)
    class_subject_id = Column(SQLUuid, ForeignKey("class_subjects.id", ondelete="CASCADE"), nullable=True, index=True)
    subject_id = Column(SQLUuid, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True, index=True)
    term_id = Column(SQLUuid, ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(SQLUuid, ForeignKey("syllabus_topics.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, default="")
    week_number = Column(Integer, nullable=True)
    sort_order = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)

    class_subject = relationship("ClassSubject", backref="syllabus_topics")
    subject_rel = relationship("Subject", foreign_keys=[subject_id])
    term = relationship("AcademicTerm")
    children = relationship("SyllabusTopic", backref=backref("parent", remote_side=[id]), cascade="all, delete-orphan")
