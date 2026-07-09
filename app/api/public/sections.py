from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.rate_limit import limiter
from app.schemas.page_section import PageSectionResponse
from app.services.page_section_service import PageSectionService
from app.services.cache_manager import cache_manager

router = APIRouter()

CACHE_KEY = "sections"


def _fetch_sections(db: Session):
    service = PageSectionService(db)
    sections = service.get_all()
    return {"sections": [PageSectionResponse.model_validate(s).model_dump() for s in sections]}


@router.get("/sections")
@limiter.limit("60/minute")
def get_sections(request: Request, db: Session = Depends(get_db)):
    return cache_manager.get_or_fetch(CACHE_KEY, lambda: _fetch_sections(db))
