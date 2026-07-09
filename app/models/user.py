from sqlalchemy import Column, String, Boolean, DateTime, JSON, CheckConstraint
from app.db.session import Base
from app.models.base import TimestampMixin
from datetime import datetime


class User(TimestampMixin, Base):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="viewer")
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    permissions = Column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'teacher', 'hr', 'proprietor', 'viewer', 'editor')", name='ck_user_role'),
    )
