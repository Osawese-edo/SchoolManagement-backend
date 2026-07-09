import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt import PyJWTError
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _load_key(path: str) -> str:
    with open(path) as f:
        return f.read()


_private_key_cache: str | None = None
_public_key_cache: str | None = None
_private_key_mtime: float = 0
_public_key_mtime: float = 0


def load_private_key() -> str:
    if settings.jwt_private_key:
        return settings.jwt_private_key
    global _private_key_cache, _private_key_mtime
    mtime = os.path.getmtime(settings.jwt_private_key_path)
    if _private_key_cache is None or mtime > _private_key_mtime:
        _private_key_cache = _load_key(settings.jwt_private_key_path)
        _private_key_mtime = mtime
    return _private_key_cache


def load_public_key() -> str:
    if settings.jwt_public_key:
        return settings.jwt_public_key
    global _public_key_cache, _public_key_mtime
    mtime = os.path.getmtime(settings.jwt_public_key_path)
    if _public_key_cache is None or mtime > _public_key_mtime:
        _public_key_cache = _load_key(settings.jwt_public_key_path)
        _public_key_mtime = mtime
    return _public_key_cache


def create_access_token(user_id: str, role: str) -> tuple[str, str, datetime]:
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "role": role,
        "jti": jti,
        "type": "access",
        "iat": now,
        "exp": expires,
    }
    private_key = load_private_key()
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token, jti, expires


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "jti": jti,
        "type": "refresh",
        "iat": now,
        "exp": expires,
    }
    private_key = load_private_key()
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token, jti, expires


def verify_token(token: str, expected_type: str = "access") -> Optional[dict]:
    try:
        public_key = load_public_key()
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        if payload.get("type") != expected_type:
            return None
        return payload
    except PyJWTError:
        return None
