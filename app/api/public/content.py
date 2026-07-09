from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.services.content_service import ContentService

router = APIRouter()


@router.get("/content/{section}")
@limiter.limit("60/minute")
def get_section_content(request: Request, section: str, db: Session = Depends(get_db)):
    service = ContentService(db)
    content = service.get_section_content(section)
    return {"section": section, "content": [
        {"field_key": c.field_key, "field_value": c.field_value, "content_type": c.content_type}
        for c in content
    ]}
