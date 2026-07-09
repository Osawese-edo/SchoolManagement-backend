from sqlalchemy import Column, String, Integer, Time, UUID as SQLUuid
from uuid import uuid4

from app.db.session import Base
from app.models.base import TimestampMixin


class TimePeriod(TimestampMixin, Base):
    __tablename__ = "time_periods"

    id = Column(SQLUuid, primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    sort_order = Column(Integer, default=0)
