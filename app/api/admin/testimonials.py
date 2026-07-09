from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timezone

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_permission, require_role
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.models.testimonial import Testimonial
from app.schemas.testimonial import TestimonialUpdate, TestimonialReply, TestimonialResponse

router = APIRouter()


@router.get("/testimonials")
@limiter.limit("120/minute")
def list_testimonials(
    request: Request,
    current_user: User = Depends(require_role("viewer")),
    db: Session = Depends(get_db),
):
    items = db.query(Testimonial).order_by(Testimonial.created_at.desc()).all()
    return {"testimonials": [TestimonialResponse.model_validate(t).model_dump() for t in items]}


@router.patch("/testimonials/{testimonial_id}")
@limiter.limit("30/minute")
def update_testimonial(
    request: Request,
    testimonial_id: UUID,
    data: TestimonialUpdate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    item = db.query(Testimonial).filter(Testimonial.id == testimonial_id).first()
    if not item:
        raise NotFoundException(detail="Testimonial not found")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return TestimonialResponse.model_validate(item).model_dump()


@router.post("/testimonials/{testimonial_id}/reply")
@limiter.limit("30/minute")
def reply_testimonial(
    request: Request,
    testimonial_id: UUID,
    data: TestimonialReply,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    item = db.query(Testimonial).filter(Testimonial.id == testimonial_id).first()
    if not item:
        raise NotFoundException(detail="Testimonial not found")
    item.admin_reply = data.admin_reply
    item.replied_at = datetime.now(timezone.utc)
    item.replied_by = current_user.id
    db.commit()
    db.refresh(item)
    return TestimonialResponse.model_validate(item).model_dump()


@router.delete("/testimonials/{testimonial_id}")
@limiter.limit("30/minute")
def delete_testimonial(
    request: Request,
    testimonial_id: UUID,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    item = db.query(Testimonial).filter(Testimonial.id == testimonial_id).first()
    if not item:
        raise NotFoundException(detail="Testimonial not found")
    db.delete(item)
    db.commit()
    return {"message": "Testimonial deleted"}
