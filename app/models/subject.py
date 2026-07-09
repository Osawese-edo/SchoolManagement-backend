from sqlalchemy import Column, String, Boolean
from app.db.session import Base
from app.models.base import TimestampMixin


class Subject(TimestampMixin, Base):
    __tablename__ = "subjects"

    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False, unique=True)
    description = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
