from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class BlogCreate(BaseModel):
    title: str
    slug: str
    content: str
    excerpt: Optional[str] = None
    author: str = "Admin"
    featured_image_url: Optional[str] = None
    is_published: bool = False


class BlogUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    author: Optional[str] = None
    featured_image_url: Optional[str] = None
    is_published: Optional[bool] = None


class BlogResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    content: str
    excerpt: Optional[str]
    author: str
    featured_image_url: Optional[str]
    is_published: bool
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
