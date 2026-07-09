from pydantic import BaseModel
from typing import Optional, Any
from uuid import UUID
from datetime import datetime


class LeadCreate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    service_type: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    preferred_contact_method: Optional[str] = None
    form_data: Optional[dict[str, Any]] = None
    notes: Optional[str] = None


class LeadStatusUpdate(BaseModel):
    status: str


class LeadNoteAdd(BaseModel):
    notes: str


class LeadEventResponse(BaseModel):
    id: UUID
    lead_id: UUID
    event_type: str
    event_metadata: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class LeadResponse(BaseModel):
    id: UUID
    full_name: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    service_type: Optional[str]
    property_type: Optional[str]
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    preferred_contact_method: Optional[str]
    form_data: Optional[dict]
    notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadDetailResponse(LeadResponse):
    events: list[LeadEventResponse] = []
