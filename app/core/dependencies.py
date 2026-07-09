from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.core.security import verify_token
from app.core.permissions import has_permission
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.models.user import User

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedException(detail="Not authenticated")
    payload = verify_token(credentials.credentials, expected_type="access")
    if payload is None:
        raise UnauthorizedException(detail="Invalid or expired token")
    user = db.query(User).filter(User.id == UUID(payload["sub"])).first()
    if user is None or not user.is_active:
        raise UnauthorizedException(detail="User not found or inactive")
    return user


def require_permission(permission: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user, permission):
            raise ForbiddenException(detail="Insufficient permissions")
        return current_user
    return checker


def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        role_hierarchy = {"viewer": 1, "teacher": 2, "editor": 2, "hr": 3, "proprietor": 4, "admin": 5}
        if role_hierarchy.get(current_user.role, 0) < role_hierarchy.get(required_role, 0):
            raise ForbiddenException(detail="Insufficient permissions")
        return current_user
    return role_checker
