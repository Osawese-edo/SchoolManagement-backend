from sqlalchemy import Column, String, Text, Boolean, Integer
from app.db.session import Base
from app.models.base import TimestampMixin


class Service(TimestampMixin, Base):
    __tablename__ = "services"

    title = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    icon_name = Column(String(50), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
