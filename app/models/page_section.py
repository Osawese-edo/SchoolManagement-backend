from sqlalchemy import Column, String, Boolean, Integer, UniqueConstraint
from app.db.session import Base
from app.models.base import TimestampMixin


class PageSection(TimestampMixin, Base):
    __tablename__ = "page_sections"
    __table_args__ = (UniqueConstraint("name"),)

    name = Column(String(50), nullable=False, index=True, unique=True)
    is_visible = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
