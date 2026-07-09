from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.schemas.lead import LeadCreate
from app.services.lead_service import LeadService
from app.services.email_service import EmailService

router = APIRouter()


@router.post("/leads", status_code=201)
@limiter.limit("10/minute")
def create_lead(request: Request, data: LeadCreate, db: Session = Depends(get_db)):
    service = LeadService(db)
    lead = service.create_lead(data.model_dump(exclude_none=True))

    EmailService().send_lead_notification({
        "id": str(lead.id),
        "full_name": lead.full_name,
        "phone": lead.phone,
        "email": lead.form_data.get("email") if lead.form_data else None,
        "service_type": lead.service_type,
        "form_data": lead.form_data,
    })

    return {"id": str(lead.id), "message": "Quote request submitted successfully"}
