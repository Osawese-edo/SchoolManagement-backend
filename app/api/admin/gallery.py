from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_permission
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.models.gallery_item import GalleryItem
from app.schemas.gallery import GalleryCreate, GalleryUpdate, GalleryResponse

router = APIRouter()


@router.get("/gallery")
@limiter.limit("120/minute")
def list_gallery(
    request: Request,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    items = db.query(GalleryItem).order_by(GalleryItem.display_order).all()
    return {"gallery": [GalleryResponse.model_validate(g).model_dump() for g in items]}


@router.post("/gallery", status_code=201)
@limiter.limit("30/minute")
def create_gallery(
    request: Request,
    data: GalleryCreate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    item = GalleryItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return GalleryResponse.model_validate(item).model_dump()


@router.patch("/gallery/{gallery_id}")
@limiter.limit("30/minute")
def update_gallery(
    request: Request,
    gallery_id: UUID,
    data: GalleryUpdate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    item = db.query(GalleryItem).filter(GalleryItem.id == gallery_id).first()
    if not item:
        raise NotFoundException(detail="Gallery item not found")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return GalleryResponse.model_validate(item).model_dump()


@router.delete("/gallery/{gallery_id}")
@limiter.limit("30/minute")
def delete_gallery(
    request: Request,
    gallery_id: UUID,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    item = db.query(GalleryItem).filter(GalleryItem.id == gallery_id).first()
    if not item:
        raise NotFoundException(detail="Gallery item not found")
    db.delete(item)
    db.commit()
    return {"message": "Gallery item deleted"}
