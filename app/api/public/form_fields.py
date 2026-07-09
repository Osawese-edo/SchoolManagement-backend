from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.models.form_field import FormField
from app.schemas.form_field import FormFieldResponse

router = APIRouter()


@router.get("/form-fields")
@limiter.limit("60/minute")
def get_form_fields(request: Request, db: Session = Depends(get_db)):
    fields = db.query(FormField).filter(
        FormField.is_active == True
    ).order_by(FormField.display_order).all()
    return {"form_fields": [FormFieldResponse.model_validate(f).model_dump() for f in fields]}
