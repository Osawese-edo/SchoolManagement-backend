from sqlalchemy import Column, String, Boolean, Integer, JSON
from app.db.session import Base
from app.models.base import TimestampMixin


class FormField(TimestampMixin, Base):
    __tablename__ = "form_fields"

    label = Column(String(100), nullable=False)
    field_type = Column(String(20), nullable=False)
    required = Column(Boolean, default=False, nullable=False)
    options = Column(JSON, nullable=True)
    placeholder = Column(String(200), nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
