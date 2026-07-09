from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.models.service import Service

router = APIRouter()


@router.get("/services")
@limiter.limit("60/minute")
def list_services(request: Request, db: Session = Depends(get_db)):
    services = (
        db.query(Service)
        .filter(Service.is_active == True)
        .order_by(Service.display_order)
        .all()
    )
    return {"services": [
        {"id": str(s.id), "title": s.title, "slug": s.slug,
         "description": s.description, "icon_name": s.icon_name,
         "display_order": s.display_order}
        for s in services
    ]}
