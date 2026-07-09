from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_role
from app.models.user import User
from app.schemas.activity_log import (
    ActivityLogResponse,
    ActivityLogListResponse,
    ActivityLogUsersResponse,
    ActivityLogUserSummary,
)
from app.services.activity_log_service import ActivityLogService

router = APIRouter()


@router.get("/activity-logs", response_model=ActivityLogListResponse)
@limiter.limit("120/minute")
def list_activity_logs(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user_id: UUID | None = Query(None),
    role: str | None = Query(None),
    resource_type: str | None = Query(None),
    action_search: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    service = ActivityLogService(db)
    logs, total = service.get_logs(
        page=page,
        per_page=per_page,
        user_id=user_id,
        role=role,
        resource_type=resource_type,
        action_search=action_search,
        start_date=start_date,
        end_date=end_date,
    )
    return ActivityLogListResponse(
        logs=[ActivityLogResponse.model_validate(l) for l in logs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/activity-logs/users", response_model=ActivityLogUsersResponse)
@limiter.limit("120/minute")
def list_activity_log_users(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    service = ActivityLogService(db)
    users = service.get_log_users()
    return ActivityLogUsersResponse(
        users=[ActivityLogUserSummary(**u) for u in users]
    )


@router.get("/activity-logs/filters")
@limiter.limit("120/minute")
def get_activity_log_filters(
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    service = ActivityLogService(db)
    return {
        "resource_types": service.get_distinct_resource_types(),
        "roles": service.get_distinct_roles(),
    }
