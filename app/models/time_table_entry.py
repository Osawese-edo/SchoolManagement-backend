from sqlalchemy import Column, String, Integer, ForeignKey, UUID as SQLUuid
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.db.session import Base
from app.models.base import TimestampMixin


class TimeTableEntry(TimestampMixin, Base):
    __tablename__ = "time_table_entries"

    id = Column(SQLUuid, primary_key=True, default=uuid4)
    class_id = Column(SQLUuid, ForeignKey("school_classes.id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)
    time_period_id = Column(SQLUuid, ForeignKey("time_periods.id"), nullable=False)
    class_subject_id = Column(SQLUuid, ForeignKey("class_subjects.id"), nullable=False)
    room = Column(String(50), nullable=True)

    class_rel = relationship("SchoolClass")
    time_period = relationship("TimePeriod")
    class_subject = relationship("ClassSubject")
