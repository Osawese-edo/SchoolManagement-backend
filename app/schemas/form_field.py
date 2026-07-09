from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class FormFieldCreate(BaseModel):
    label: str
    field_type: str
    required: bool = False
    options: Optional[list[str]] = None
    placeholder: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


class FormFieldUpdate(BaseModel):
    label: Optional[str] = None
    field_type: Optional[str] = None
    required: Optional[bool] = None
    options: Optional[list[str]] = None
    placeholder: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class FormFieldResponse(BaseModel):
    id: UUID
    label: str
    field_type: str
    required: bool
    options: Optional[list[str]]
    placeholder: Optional[str]
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
