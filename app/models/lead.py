from sqlalchemy import Column, String, Text, Integer, JSON
from app.db.session import Base
from app.models.base import TimestampMixin


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"

    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    location = Column(String(200), nullable=True)
    service_type = Column(String(50), nullable=True)
    property_type = Column(String(50), nullable=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Integer, nullable=True)
    preferred_contact_method = Column(String(20), nullable=True)
    form_data = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="new")
