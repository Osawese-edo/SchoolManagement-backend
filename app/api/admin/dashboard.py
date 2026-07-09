from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_role
from app.models.user import User
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/dashboard")
@limiter.limit("120/minute")
def get_dashboard(
    request: Request,
    months: int = Query(6, ge=1, le=24),
    current_user: User = Depends(require_role("viewer")),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    return {
        "metrics": service.get_metrics(),
        "leads_by_status": service.get_leads_by_status(),
        "monthly_leads": service.get_monthly_leads(months),
    }
