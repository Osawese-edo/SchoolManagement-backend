from sqlalchemy import Column, String, Text, Boolean, DateTime
from app.db.session import Base
from app.models.base import TimestampMixin


class BlogPost(TimestampMixin, Base):
    __tablename__ = "blog_posts"

    title = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False)
    excerpt = Column(Text, nullable=True)
    author = Column(String(100), nullable=False, default="Admin")
    featured_image_url = Column(String(500), nullable=True)
    is_published = Column(Boolean, default=False, nullable=False)
    published_at = Column(DateTime, nullable=True)
