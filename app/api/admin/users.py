from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_role
from app.core.exceptions import ConflictException, NotFoundException, BadRequestException
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.log_helper import log_action
from app.services.sse_manager import sse_manager

router = APIRouter()


@router.get("/users")
@limiter.limit("120/minute")
def list_users(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    users = db.query(User).all()
    return {"users": [UserResponse.model_validate(u).model_dump() for u in users]}


@router.post("/users", status_code=201)
@limiter.limit("30/minute")
def create_user(
    request: Request,
    data: UserCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise ConflictException(detail="Email already exists")
    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(db, current_user, "Created user", "user", str(user.id), {"email": user.email, "role": user.role})
    return UserResponse.model_validate(user).model_dump()


@router.patch("/users/{user_id}")
@limiter.limit("30/minute")
async def update_user(
    request: Request,
    user_id: UUID,
    data: UserUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException(detail="User not found")
    was_admin = user.role == "admin"
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    if was_admin and user.role != "admin":
        remaining = db.query(User).filter(User.role == "admin", User.is_active == True).count()
        if remaining == 0:
            await sse_manager.update_admin_exists(False)
    log_action(db, current_user, "Updated user", "user", str(user.id))
    return UserResponse.model_validate(user).model_dump()


@router.delete("/users/{user_id}")
@limiter.limit("30/minute")
async def delete_user(
    request: Request,
    user_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if current_user.id == user_id:
        raise BadRequestException(detail="Cannot delete yourself")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundException(detail="User not found")
    was_admin = user.role == "admin"
    db.delete(user)
    db.commit()
    if was_admin:
        remaining = db.query(User).filter(User.role == "admin", User.is_active == True).count()
        if remaining == 0:
            await sse_manager.update_admin_exists(False)
    log_action(db, current_user, "Deleted user", "user", str(user.id), {"email": user.email, "role": user.role})
    return {"message": "User deleted"}
