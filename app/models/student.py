from sqlalchemy import Column, String, ForeignKey, Boolean, Date, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base import TimestampMixin


class Student(TimestampMixin, Base):
    __tablename__ = "students"

    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False)
    admission_number = Column(String(50), unique=True, nullable=False, index=True)
    current_class_id = Column(UUID(as_uuid=True), ForeignKey("school_classes.id", ondelete="SET NULL"), index=True, nullable=True)
    status = Column(String(20), default="active", nullable=False, index=True)
    date_of_admission = Column(Date, nullable=True)
    home_address = Column(Text, nullable=True)
    parent_name = Column(String(200), nullable=True)
    parent_phone = Column(String(20), nullable=True)
    parent_whatsapp = Column(String(20), nullable=True)
    parent_relationship = Column(String(50), nullable=True)
    emergency_contact = Column(String(20), nullable=True)
    alt_emergency_contact = Column(String(20), nullable=True)
    medical_conditions = Column(Text, nullable=True)
    blood_group = Column(String(5), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)
    passport_photo_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    current_class_rel = relationship("SchoolClass", foreign_keys=[current_class_id])
