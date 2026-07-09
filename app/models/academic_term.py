from sqlalchemy import Column, String, Date, Boolean
from app.db.session import Base
from app.models.base import TimestampMixin


class AcademicTerm(TimestampMixin, Base):
    __tablename__ = "academic_terms"

    name = Column(String(100), nullable=False)
    year = Column(String(20), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
