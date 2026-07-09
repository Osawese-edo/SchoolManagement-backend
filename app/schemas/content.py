from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class ContentCreate(BaseModel):
    section: str
    field_key: str
    field_value: str
    content_type: str = "text"
    is_active: bool = True


class ContentUpdate(BaseModel):
    field_key: Optional[str] = None
    field_value: Optional[str] = None
    is_active: Optional[bool] = None


class ContentBulkUpdate(BaseModel):
    updates: list[dict]


class ContentResponse(BaseModel):
    id: UUID
    section: str
    field_key: str
    field_value: Optional[str]
    content_type: str
    is_active: bool
    updated_at: datetime

    class Config:
        from_attributes = True
