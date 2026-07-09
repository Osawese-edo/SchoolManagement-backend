from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_permission
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.schemas.content import ContentCreate, ContentUpdate, ContentBulkUpdate, ContentResponse
from app.services.content_service import ContentService
from app.services.cache_manager import cache_manager

router = APIRouter()


def _invalidate_content_cache():
    cache_manager.invalidate_by_prefix("config:")
    cache_manager.invalidate_by_prefix("theme")


@router.post("/content", status_code=201)
@limiter.limit("30/minute")
def create_content(
    request: Request,
    data: ContentCreate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = ContentService(db)
    content = service.create_content(data.model_dump())
    _invalidate_content_cache()
    return ContentResponse.model_validate(content).model_dump()


@router.get("/content")
@limiter.limit("120/minute")
def list_content(
    request: Request,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = ContentService(db)
    content = service.get_all_content()
    return {"content": [
        ContentResponse.model_validate(c).model_dump() for c in content
    ]}


@router.patch("/content/{content_id}")
@limiter.limit("30/minute")
def update_content(
    request: Request,
    content_id: UUID,
    data: ContentUpdate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = ContentService(db)
    updated = service.update_content(content_id, data.model_dump(exclude_none=True))
    if not updated:
        raise NotFoundException(detail="Content not found")
    _invalidate_content_cache()
    return ContentResponse.model_validate(updated).model_dump()


@router.delete("/content/{content_id}")
@limiter.limit("30/minute")
def delete_content(
    request: Request,
    content_id: UUID,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = ContentService(db)
    deleted = service.delete_content(content_id)
    if not deleted:
        raise NotFoundException(detail="Content not found")
    _invalidate_content_cache()
    return {"message": "Content deleted"}


@router.post("/content/bulk")
@limiter.limit("30/minute")
def bulk_update(
    request: Request,
    data: ContentBulkUpdate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = ContentService(db)
    results = service.bulk_update(data.updates)
    _invalidate_content_cache()
    return {"content": [
        ContentResponse.model_validate(c).model_dump() for c in results
    ]}
