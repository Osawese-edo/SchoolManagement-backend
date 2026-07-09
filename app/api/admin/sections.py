from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_permission
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.page_section import PageSectionResponse, PageSectionUpdate
from app.services.page_section_service import PageSectionService
from app.services.cache_manager import cache_manager

router = APIRouter()


@router.get("/sections")
@limiter.limit("120/minute")
def list_sections(
    request: Request,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = PageSectionService(db)
    sections = service.get_all()
    return {"sections": [PageSectionResponse.model_validate(s).model_dump() for s in sections]}


@router.patch("/sections/{name}")
@limiter.limit("30/minute")
def update_section(
    request: Request,
    name: str,
    data: PageSectionUpdate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = PageSectionService(db)
    updated = service.update(name, data.model_dump(exclude_none=True))
    if not updated:
        raise NotFoundException(detail="Section not found")
    cache_manager.invalidate_by_prefix("sections")
    return PageSectionResponse.model_validate(updated).model_dump()
