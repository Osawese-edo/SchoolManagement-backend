from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class ServiceCreate(BaseModel):
    title: str
    slug: Optional[str] = None
    description: Optional[str] = None
    icon_name: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


class ServiceUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon_name: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class ServiceResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: Optional[str]
    icon_name: Optional[str]
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
