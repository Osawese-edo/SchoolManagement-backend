import secrets
from fastapi import APIRouter, Depends, Query
from app.core.exceptions import NotFoundException, ConflictException, BadRequestException, ForbiddenException
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_permission
from app.models.user import User
from app.models.staff import Staff
from app.core.permissions import (
    STAFF_VIEW, STAFF_CREATE, STAFF_EDIT, STAFF_DELETE,
    get_default_permissions,
)
from app.core.security import hash_password
from app.schemas.staff import StaffCreate, StaffUpdate, StaffResponse, StaffDetail

router = APIRouter()


def _check_staff_visible_or_404(staff: Staff, current_user: User) -> None:
    """Raise NotFoundException if current_user cannot see this staff record."""
    if current_user.role == "hr" and staff.role != "teacher":
        raise NotFoundException("Staff not found")
    if current_user.role == "proprietor" and staff.role not in ("teacher", "hr"):
        raise NotFoundException("Staff not found")


def _restricted_roles_for(current_user: User) -> set[str]:
    """Return set of roles the current_user is not allowed to assign."""
    if current_user.role == "hr":
        return {"hr", "viewer", "editor", "proprietor", "admin"}
    if current_user.role == "proprietor":
        return {"editor", "proprietor", "admin"}
    return set()


@router.get("/staff", response_model=list[StaffDetail])
def list_staff(
    search: str | None = Query(None),
    role: str | None = Query(None),
    current_user: User = Depends(require_permission(STAFF_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Staff).outerjoin(User, Staff.user_id == User.id)

    if current_user.role == "hr":
        query = query.filter(Staff.role == "teacher")
    elif current_user.role == "proprietor":
        query = query.filter(Staff.role.in_(["teacher", "hr"]))

    if role:
        query = query.filter(Staff.role == role)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            Staff.first_name.ilike(pattern) |
            Staff.last_name.ilike(pattern) |
            Staff.email.ilike(pattern) |
            Staff.employee_id.ilike(pattern)
        )

    staff = query.order_by(Staff.created_at.asc()).all()
    return [
        StaffDetail(
            id=s.id,
            first_name=s.first_name,
            last_name=s.last_name,
            full_name=f"{s.first_name} {s.last_name}",
            email=s.email,
            phone=s.phone,
            home_address=s.home_address,
            employee_id=s.employee_id,
            role=s.role,
            specialization=s.specialization,
            qualification=s.qualification,
            date_hired=s.date_hired,
            user_id=s.user_id,
            user_email=s.user_rel.email if s.user_rel else None,
            user_role=s.user_rel.role if s.user_rel else None,
            permissions=s.user_rel.permissions if s.user_rel else None,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in staff
    ]


@router.get("/staff/{staff_id}", response_model=StaffDetail)
def get_staff(
    staff_id: UUID,
    current_user: User = Depends(require_permission(STAFF_VIEW)),
    db: Session = Depends(get_db),
):
    s = db.query(Staff).outerjoin(User, Staff.user_id == User.id).filter(Staff.id == staff_id).first()
    if not s:
        raise NotFoundException("Staff not found")
    _check_staff_visible_or_404(s, current_user)
    return StaffDetail(
        id=s.id,
        first_name=s.first_name,
        last_name=s.last_name,
        full_name=f"{s.first_name} {s.last_name}",
        email=s.email,
        phone=s.phone,
        home_address=s.home_address,
        employee_id=s.employee_id,
        role=s.role,
        specialization=s.specialization,
        qualification=s.qualification,
        date_hired=s.date_hired,
        user_id=s.user_id,
        user_email=s.user_rel.email if s.user_rel else None,
        user_role=s.user_rel.role if s.user_rel else None,
        permissions=s.user_rel.permissions if s.user_rel else None,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.post("/staff", response_model=StaffDetail, status_code=201)
def create_staff(
    data: StaffCreate,
    current_user: User = Depends(require_permission(STAFF_CREATE)),
    db: Session = Depends(get_db),
):
    restricted = _restricted_roles_for(current_user)
    if data.role in restricted:
        role_label = ", ".join(sorted(restricted))
        raise ForbiddenException(f"You cannot assign {role_label} roles")

    if data.email:
        existing = db.query(Staff).filter(Staff.email == data.email).first()
        if existing:
            raise ConflictException("Email already exists")

    if data.employee_id:
        existing = db.query(Staff).filter(Staff.employee_id == data.employee_id).first()
        if existing:
            raise ConflictException("Employee ID already exists")

    login_email = data.login_email or data.email
    user_id = None
    if current_user.role == "hr":
        permissions = get_default_permissions(data.role)
    else:
        permissions = data.permissions or get_default_permissions(data.role)

    if data.create_login:
        if not login_email:
            raise BadRequestException("Email is required to create a login account")
        existing_user = db.query(User).filter(User.email == login_email).first()
        if existing_user:
            raise ConflictException("Login email already exists")
        user = User(
            email=login_email,
            full_name=f"{data.first_name} {data.last_name}",
            password_hash=hash_password(data.login_password or secrets.token_urlsafe(12)),
            role=data.role,
            permissions=permissions,
        )
        db.add(user)
        db.flush()
        user_id = user.id

    staff = Staff(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        home_address=data.home_address,
        employee_id=data.employee_id,
        role=data.role,
        specialization=data.specialization,
        qualification=data.qualification,
        date_hired=data.date_hired,
        user_id=user_id,
        is_active=data.is_active,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    if staff.user_rel:
        db.refresh(staff.user_rel)

    return StaffDetail(
        id=staff.id,
        first_name=staff.first_name,
        last_name=staff.last_name,
        full_name=f"{staff.first_name} {staff.last_name}",
        email=staff.email,
        phone=staff.phone,
        home_address=staff.home_address,
        employee_id=staff.employee_id,
        role=staff.role,
        specialization=staff.specialization,
        qualification=staff.qualification,
        date_hired=staff.date_hired,
        user_id=staff.user_id,
        user_email=staff.user_rel.email if staff.user_rel else None,
        user_role=staff.user_rel.role if staff.user_rel else None,
        permissions=staff.user_rel.permissions if staff.user_rel else None,
        is_active=staff.is_active,
        created_at=staff.created_at,
        updated_at=staff.updated_at,
    )


@router.patch("/staff/{staff_id}", response_model=StaffDetail)
def update_staff(
    staff_id: UUID,
    data: StaffUpdate,
    current_user: User = Depends(require_permission(STAFF_EDIT)),
    db: Session = Depends(get_db),
):
    s = db.query(Staff).filter(Staff.id == staff_id).first()
    if not s:
        raise NotFoundException("Staff not found")
    _check_staff_visible_or_404(s, current_user)

    if data.first_name is not None:
        s.first_name = data.first_name
    if data.last_name is not None:
        s.last_name = data.last_name
    if data.email is not None:
        s.email = data.email
    if data.phone is not None:
        s.phone = data.phone
    if data.home_address is not None:
        s.home_address = data.home_address
    if data.employee_id is not None:
        s.employee_id = data.employee_id
    if data.role is not None:
        restricted = _restricted_roles_for(current_user)
        if data.role in restricted:
            role_label = ", ".join(sorted(restricted))
            raise ForbiddenException(f"You cannot assign {role_label} roles")
        s.role = data.role
    if data.specialization is not None:
        s.specialization = data.specialization
    if data.qualification is not None:
        s.qualification = data.qualification
    if data.date_hired is not None:
        s.date_hired = data.date_hired
    if data.is_active is not None:
        s.is_active = data.is_active

    if s.user_id and data.login_email is not None:
        user = db.query(User).filter(User.id == s.user_id).first()
        if user:
            user.email = data.login_email
    if s.user_id and data.login_password is not None:
        user = db.query(User).filter(User.id == s.user_id).first()
        if user:
            user.password_hash = hash_password(data.login_password)
    if s.user_id and data.permissions is not None and current_user.role != "hr":
        user = db.query(User).filter(User.id == s.user_id).first()
        if user:
            user.permissions = data.permissions
    if s.user_id and data.role is not None:
        user = db.query(User).filter(User.id == s.user_id).first()
        if user:
            user.role = data.role

    db.commit()
    db.refresh(s)

    return StaffDetail(
        id=s.id,
        first_name=s.first_name,
        last_name=s.last_name,
        full_name=f"{s.first_name} {s.last_name}",
        email=s.email,
        phone=s.phone,
        home_address=s.home_address,
        employee_id=s.employee_id,
        role=s.role,
        specialization=s.specialization,
        qualification=s.qualification,
        date_hired=s.date_hired,
        user_id=s.user_id,
        user_email=s.user_rel.email if s.user_rel else None,
        user_role=s.user_rel.role if s.user_rel else None,
        permissions=s.user_rel.permissions if s.user_rel else None,
        is_active=s.is_active,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


@router.delete("/staff/{staff_id}")
def delete_staff(
    staff_id: UUID,
    current_user: User = Depends(require_permission(STAFF_DELETE)),
    db: Session = Depends(get_db),
):
    s = db.query(Staff).filter(Staff.id == staff_id).first()
    if not s:
        raise NotFoundException("Staff not found")
    _check_staff_visible_or_404(s, current_user)

    from app.models.school_class import SchoolClass
    from app.models.class_subject import ClassSubject

    db.query(SchoolClass).filter(SchoolClass.teacher_id == staff_id).update({"teacher_id": None})
    db.query(ClassSubject).filter(ClassSubject.teacher_id == staff_id).update({"teacher_id": None})

    if s.user_id:
        user = db.query(User).filter(User.id == s.user_id).first()
        if user:
            db.delete(user)

    db.delete(s)
    db.commit()
    return {"message": "Staff deleted"}
