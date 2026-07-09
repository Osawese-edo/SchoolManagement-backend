from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.rate_limit import limiter
from app.services.content_service import ContentService
from app.services.cache_manager import cache_manager

router = APIRouter()

CACHE_KEY = "theme"


def _fetch_theme(db: Session):
    service = ContentService(db)
    content = service.get_section_content("theme")
    theme = {}
    for c in content:
        theme[c.field_key] = c.field_value
    return theme


@router.get("/theme")
@limiter.limit("60/minute")
def get_theme(request: Request, db: Session = Depends(get_db)):
    return cache_manager.get_or_fetch(CACHE_KEY, lambda: _fetch_theme(db))
