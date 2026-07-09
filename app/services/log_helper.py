from sqlalchemy.orm import Session
from app.models.user import User
from app.services.activity_log_service import ActivityLogService


def log_action(
    db: Session,
    user: User,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
):
    ActivityLogService(db).log_action(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )
