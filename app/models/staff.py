from sqlalchemy import Column, String, ForeignKey, Boolean, Date, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import TimestampMixin


class Staff(TimestampMixin, Base):
    __tablename__ = "staff"

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True, unique=True)
    phone = Column(String(20), nullable=True)
    home_address = Column(Text, nullable=True)
    employee_id = Column(String(50), unique=True, nullable=True)
    role = Column(String(20), nullable=False)
    specialization = Column(String(100), nullable=True)
    qualification = Column(String(200), nullable=True)
    date_hired = Column(Date, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    user_rel = relationship("User", foreign_keys=[user_id])
