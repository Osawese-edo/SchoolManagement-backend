from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.activity_log import ActivityLog
from app.models.user import User


class ActivityLogService:
    def __init__(self, db: Session):
        self.db = db

    def log_action(
        self,
        user: User,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict | None = None,
    ) -> ActivityLog:
        log = ActivityLog(
            user_id=user.id,
            user_name=user.full_name or user.email,
            user_role=user.role,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            details=details,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        self.db.commit()
        return log

    def get_logs(
        self,
        page: int = 1,
        per_page: int = 50,
        user_id: UUID | None = None,
        role: str | None = None,
        resource_type: str | None = None,
        action_search: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[ActivityLog], int]:
        query = self.db.query(ActivityLog)

        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        if role:
            query = query.filter(ActivityLog.user_role == role)
        if resource_type:
            query = query.filter(ActivityLog.resource_type == resource_type)
        if action_search:
            query = query.filter(ActivityLog.action.ilike(f"%{action_search}%"))
        if start_date:
            query = query.filter(ActivityLog.created_at >= start_date)
        if end_date:
            query = query.filter(ActivityLog.created_at <= end_date)

        total = query.count()
        logs = query.order_by(desc(ActivityLog.created_at)).offset(
            (page - 1) * per_page
        ).limit(per_page).all()

        return logs, total

    def get_log_users(self) -> list[dict]:
        rows = self.db.query(
            ActivityLog.user_id,
            ActivityLog.user_name,
            ActivityLog.user_role,
            func.count(ActivityLog.id).label("log_count"),
        ).group_by(
            ActivityLog.user_id,
            ActivityLog.user_name,
            ActivityLog.user_role,
        ).order_by(desc("log_count")).all()

        return [
            {"user_id": r[0], "user_name": r[1], "user_role": r[2], "log_count": r[3]}
            for r in rows
        ]

    def get_distinct_resource_types(self) -> list[str]:
        rows = self.db.query(ActivityLog.resource_type).filter(
            ActivityLog.resource_type.isnot(None)
        ).distinct().order_by(ActivityLog.resource_type).all()
        return [r[0] for r in rows]

    def get_distinct_roles(self) -> list[str]:
        rows = self.db.query(ActivityLog.user_role).distinct().order_by(ActivityLog.user_role).all()
        return [r[0] for r in rows]
