from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.models.testimonial import Testimonial

router = APIRouter()


@router.get("/testimonials")
@limiter.limit("60/minute")
def list_testimonials(request: Request, db: Session = Depends(get_db)):
    items = (
        db.query(Testimonial)
        .filter(Testimonial.is_published == True)
        .order_by(Testimonial.created_at.desc())
        .all()
    )
    return {"testimonials": [
        {"id": str(t.id), "customer_name": t.customer_name,
         "rating": t.rating, "review_text": t.review_text,
         "admin_reply": t.admin_reply, "created_at": t.created_at.isoformat()}
        for t in items
    ]}
