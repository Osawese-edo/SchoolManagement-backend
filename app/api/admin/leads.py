from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_permission
from app.core.permissions import LEADS_VIEW
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.lead import (
    LeadResponse, LeadDetailResponse, LeadStatusUpdate,
    LeadNoteAdd, LeadEventResponse
)
from app.services.lead_service import LeadService

router = APIRouter()


@router.get("/leads")
@limiter.limit("120/minute")
def list_leads(
    request: Request,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_permission(LEADS_VIEW)),
    db: Session = Depends(get_db),
):
    service = LeadService(db)
    skip = (page - 1) * per_page
    leads, total = service.get_leads(status, search, skip, per_page)
    return {
        "leads": [LeadResponse.model_validate(l).model_dump() for l in leads],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/leads/{lead_id}")
@limiter.limit("120/minute")
def get_lead(
    request: Request,
    lead_id: UUID,
    current_user: User = Depends(require_permission(LEADS_VIEW)),
    db: Session = Depends(get_db),
):
    service = LeadService(db)
    lead = service.get_lead(lead_id)
    if not lead:
        raise NotFoundException(detail="Lead not found")
    events = lead.events if hasattr(lead, 'events') else []
    return LeadDetailResponse(
        **LeadResponse.model_validate(lead).model_dump(),
        events=[LeadEventResponse.model_validate(e).model_dump() for e in events]
    ).model_dump()


@router.patch("/leads/{lead_id}/status")
@limiter.limit("30/minute")
def update_lead_status(
    request: Request,
    lead_id: UUID,
    data: LeadStatusUpdate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = LeadService(db)
    lead = service.update_status(lead_id, data.status, current_user)
    if not lead:
        raise NotFoundException(detail="Lead not found")
    return LeadResponse.model_validate(lead).model_dump()


@router.post("/leads/{lead_id}/note")
@limiter.limit("30/minute")
def add_lead_note(
    request: Request,
    lead_id: UUID,
    data: LeadNoteAdd,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = LeadService(db)
    lead = service.add_note(lead_id, data.notes, current_user)
    if not lead:
        raise NotFoundException(detail="Lead not found")
    return LeadResponse.model_validate(lead).model_dump()


@router.delete("/leads/{lead_id}")
@limiter.limit("30/minute")
def delete_lead(
    request: Request,
    lead_id: UUID,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = LeadService(db)
    if not service.delete_lead(lead_id):
        raise NotFoundException(detail="Lead not found")
    return {"message": "Lead deleted"}
