from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_permission
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.models.form_field import FormField
from app.schemas.form_field import FormFieldCreate, FormFieldUpdate, FormFieldResponse

router = APIRouter()


@router.get("/form-fields")
@limiter.limit("120/minute")
def list_form_fields(
    request: Request,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    fields = db.query(FormField).order_by(FormField.display_order).all()
    return {"form_fields": [FormFieldResponse.model_validate(f).model_dump() for f in fields]}


@router.post("/form-fields", status_code=201)
@limiter.limit("30/minute")
def create_form_field(
    request: Request,
    data: FormFieldCreate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    field = FormField(**data.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return FormFieldResponse.model_validate(field).model_dump()


@router.patch("/form-fields/{field_id}")
@limiter.limit("30/minute")
def update_form_field(
    request: Request,
    field_id: UUID,
    data: FormFieldUpdate,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    field = db.query(FormField).filter(FormField.id == field_id).first()
    if not field:
        raise NotFoundException(detail="Form field not found")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(field, key, value)
    db.commit()
    db.refresh(field)
    return FormFieldResponse.model_validate(field).model_dump()


@router.delete("/form-fields/{field_id}")
@limiter.limit("30/minute")
def delete_form_field(
    request: Request,
    field_id: UUID,
    current_user: User = Depends(require_permission("content:manage")),
    db: Session = Depends(get_db),
):
    field = db.query(FormField).filter(FormField.id == field_id).first()
    if not field:
        raise NotFoundException(detail="Form field not found")
    db.delete(field)
    db.commit()
    return {"message": "Form field deleted"}
