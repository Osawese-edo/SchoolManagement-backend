from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from app.models.site_content import SiteContent
from app.services.cache_manager import cache_manager

router = APIRouter()

CACHE_KEY = "config:contact"


def _fetch_contact(db: Session):
    content_map = {
        c.field_key: c.field_value
        for c in db.query(SiteContent).filter(
            SiteContent.section == "contact",
            SiteContent.is_active == True,
        ).all()
    }
    return {
        "company_name": content_map.get("company_name") or "DESTINED CHAMPIONS FOUNDATION",
        "whatsapp": (
            content_map.get("whatsapp")
            or settings.whatsapp_number
        ),
        "phone": content_map.get("phone") or "+15550000",
        "email": content_map.get("email") or "info@destinedchampions.com",
        "hours": content_map.get("working_hours") or "Mon-Fri: 8:00 AM - 3:00 PM",
        "address": content_map.get("address") or "123 Education Avenue, City, State 12345",
        "google_maps_url": content_map.get("google_maps_url") or "",
        "logo_svg": content_map.get("logo_svg") or "",
    }


@router.get("/config/contact")
@limiter.limit("60/minute")
def get_contact_info(request: Request, db: Session = Depends(get_db)):
    return cache_manager.get_or_fetch(CACHE_KEY, lambda: _fetch_contact(db))
