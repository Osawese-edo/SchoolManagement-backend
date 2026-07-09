from pydantic import BaseModel, model_validator
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.services.gallery_service import get_storage_type


class GalleryCreate(BaseModel):
    category: str
    before_image_url: str
    after_image_url: str
    caption: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


class GalleryUpdate(BaseModel):
    category: Optional[str] = None
    before_image_url: Optional[str] = None
    after_image_url: Optional[str] = None
    caption: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class GalleryResponse(BaseModel):
    id: UUID
    category: str
    before_image_url: str
    after_image_url: str
    before_storage: str = "local"
    after_storage: str = "local"
    caption: Optional[str]
    display_order: int
    is_active: bool
    created_at: datetime

    @model_validator(mode="after")
    def resolve_storage(self):
        self.before_storage = get_storage_type(self.before_image_url)
        self.after_storage = get_storage_type(self.after_image_url)
        return self

    class Config:
        from_attributes = True
