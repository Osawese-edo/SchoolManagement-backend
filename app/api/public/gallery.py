from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.models.gallery_item import GalleryItem
from app.services.gallery_service import get_storage_type

router = APIRouter()


@router.get("/gallery")
@limiter.limit("60/minute")
def list_gallery(request: Request, db: Session = Depends(get_db)):
    items = (
        db.query(GalleryItem)
        .filter(GalleryItem.is_active == True)
        .order_by(GalleryItem.display_order)
        .all()
    )
    return {"gallery": [
        {"id": str(g.id), "category": g.category,
         "before_image_url": g.before_image_url,
         "after_image_url": g.after_image_url,
         "caption": g.caption,
         "before_storage": get_storage_type(g.before_image_url),
         "after_storage": get_storage_type(g.after_image_url)}
        for g in items
    ]}
