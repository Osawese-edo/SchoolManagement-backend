from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import date, datetime


class StaffCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    home_address: Optional[str] = None
    employee_id: Optional[str] = None
    role: str = "teacher"
    specialization: Optional[str] = None
    qualification: Optional[str] = None
    date_hired: Optional[date] = None
    is_active: bool = True
    create_login: bool = False
    login_email: Optional[str] = None
    login_password: Optional[str] = None
    permissions: Optional[list[str]] = None


class StaffUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    home_address: Optional[str] = None
    employee_id: Optional[str] = None
    role: Optional[str] = None
    specialization: Optional[str] = None
    qualification: Optional[str] = None
    date_hired: Optional[date] = None
    is_active: Optional[bool] = None
    login_email: Optional[str] = None
    login_password: Optional[str] = None
    permissions: Optional[list[str]] = None


class StaffResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: Optional[str]
    phone: Optional[str]
    employee_id: Optional[str]
    home_address: Optional[str]
    role: str
    specialization: Optional[str]
    qualification: Optional[str]
    date_hired: Optional[date]
    user_id: Optional[UUID]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StaffDetail(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    home_address: Optional[str]
    employee_id: Optional[str]
    role: str
    specialization: Optional[str]
    qualification: Optional[str]
    date_hired: Optional[date]
    user_id: Optional[UUID]
    user_email: Optional[str]
    user_role: Optional[str]
    permissions: Optional[list[str]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
