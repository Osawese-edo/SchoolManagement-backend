from sqlalchemy import Column, String, Text, Boolean, Integer
from app.db.session import Base
from app.models.base import TimestampMixin


class GalleryItem(TimestampMixin, Base):
    __tablename__ = "gallery_items"

    category = Column(String(50), nullable=False, index=True)
    before_image_url = Column(String(500), nullable=False)
    after_image_url = Column(String(500), nullable=False)
    caption = Column(String(200), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
