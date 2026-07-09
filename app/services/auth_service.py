from sqlalchemy.orm import Session
from uuid import UUID

from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from datetime import datetime, timezone


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def login(self, email: str, password: str) -> dict:
        user = self.db.query(User).filter(User.email == email).first()
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is inactive")

        user.last_login = datetime.now(timezone.utc)

        access_token, access_jti, access_exp = create_access_token(str(user.id), user.role)
        refresh_token, refresh_jti, refresh_exp = create_refresh_token(str(user.id))

        rt = RefreshToken(
            user_id=user.id,
            token_jti=refresh_jti,
            expires_at=refresh_exp,
        )
        self.db.add(rt)
        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    def refresh(self, refresh_token_str: str) -> dict:
        payload = verify_token(refresh_token_str, expected_type="refresh")
        if payload is None:
            raise ValueError("Invalid or expired refresh token")

        token_jti = payload["jti"]
        stored_token = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token_jti == token_jti, RefreshToken.is_revoked == False)
            .first()
        )
        if not stored_token:
            raise ValueError("Refresh token revoked or not found")

        stored_token.is_revoked = True

        user = self.db.query(User).filter(User.id == UUID(payload["sub"])).first()
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        access_token, _, _ = create_access_token(str(user.id), user.role)
        new_refresh_token, new_jti, new_exp = create_refresh_token(str(user.id))

        rt = RefreshToken(
            user_id=user.id,
            token_jti=new_jti,
            expires_at=new_exp,
        )
        self.db.add(rt)
        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
        }

    def logout(self, user_id: UUID):
        tokens = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)
            .all()
        )
        for token in tokens:
            token.is_revoked = True
        self.db.commit()

    def check_admin_exists(self) -> bool:
        return self.db.query(User).filter(User.role == "admin").first() is not None

    def create_first_admin(self, email: str, password: str, full_name: str) -> User:
        if self.check_admin_exists():
            raise ValueError("An admin user already exists")
        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
