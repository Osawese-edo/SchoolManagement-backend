from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class TestimonialCreate(BaseModel):
    customer_name: str
    rating: int = Field(ge=1, le=5)
    review_text: str


class TestimonialUpdate(BaseModel):
    customer_name: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    review_text: Optional[str] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None


class TestimonialReply(BaseModel):
    admin_reply: str


class TestimonialResponse(BaseModel):
    id: UUID
    customer_name: str
    rating: int
    review_text: str
    is_published: bool
    is_featured: bool
    admin_reply: Optional[str]
    replied_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
