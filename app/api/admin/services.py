import re
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_permission
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceUpdate, ServiceResponse

router = APIRouter()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "", text.lower().replace(" ", "-")).strip("-")


@router.get("/services")
@limiter.limit("120/minute")
def list_services(
    request: Request,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    services = db.query(Service).order_by(Service.display_order).all()
    return {"services": [ServiceResponse.model_validate(s).model_dump() for s in services]}


def _reorder_services(db: Session, target_order: int, exclude_id=None):
    """Shift services down to make room for target_order."""
    query = db.query(Service).filter(
        Service.display_order >= target_order,
    )
    if exclude_id:
        query = query.filter(Service.id != exclude_id)
    to_shift = query.order_by(Service.display_order).all()
    for s in to_shift:
        s.display_order += 1


@router.post("/services", status_code=201)
@limiter.limit("30/minute")
def create_service(
    request: Request,
    data: ServiceCreate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    payload = data.model_dump()
    if not payload.get("slug"):
        base_slug = _slugify(payload["title"])
        slug = base_slug
        counter = 1
        while db.query(Service).filter(Service.slug == slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        payload["slug"] = slug
    _reorder_services(db, payload["display_order"])
    service = Service(**payload)
    db.add(service)
    db.commit()
    db.refresh(service)
    return ServiceResponse.model_validate(service).model_dump()


@router.patch("/services/{service_id}")
@limiter.limit("30/minute")
def update_service(
    request: Request,
    service_id: UUID,
    data: ServiceUpdate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise NotFoundException(detail="Service not found")
    update_data = data.model_dump(exclude_none=True)
    if "display_order" in update_data and update_data["display_order"] != service.display_order:
        _reorder_services(db, update_data["display_order"], exclude_id=service_id)
    for key, value in update_data.items():
        setattr(service, key, value)
    db.commit()
    db.refresh(service)
    return ServiceResponse.model_validate(service).model_dump()


@router.delete("/services/{service_id}")
@limiter.limit("30/minute")
def delete_service(
    request: Request,
    service_id: UUID,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise NotFoundException(detail="Service not found")
    deleted_order = service.display_order
    db.delete(service)
    db.flush()
    for s in db.query(Service).filter(Service.display_order > deleted_order).order_by(Service.display_order).all():
        s.display_order -= 1
    db.commit()
    return {"message": "Service deleted"}
