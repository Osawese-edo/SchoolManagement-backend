from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PageSectionResponse(BaseModel):
    name: str
    is_visible: bool
    display_order: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PageSectionUpdate(BaseModel):
    is_visible: Optional[bool] = None
    display_order: Optional[int] = None
