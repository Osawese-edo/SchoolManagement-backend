from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ActivityLogResponse(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str
    user_role: str
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityLogListResponse(BaseModel):
    logs: list[ActivityLogResponse]
    total: int
    page: int
    per_page: int


class ActivityLogUserSummary(BaseModel):
    user_id: UUID
    user_name: str
    user_role: str
    log_count: int


class ActivityLogUsersResponse(BaseModel):
    users: list[ActivityLogUserSummary]
