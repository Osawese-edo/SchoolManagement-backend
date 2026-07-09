from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta, timezone

from app.models.lead import Lead
from app.models.testimonial import Testimonial
from app.models.service import Service
from app.models.gallery_item import GalleryItem


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def get_metrics(self) -> dict:
        total_leads = self.db.query(Lead).count()
        new_leads_today = self.db.query(Lead).filter(
            func.date(Lead.created_at) == datetime.now(timezone.utc).date()
        ).count()
        pending_reviews = self.db.query(Testimonial).filter(Testimonial.is_published == False).count()
        active_services = self.db.query(Service).filter(Service.is_active == True).count()
        total_gallery = self.db.query(GalleryItem).count()
        published_testimonials = self.db.query(Testimonial).filter(Testimonial.is_published == True).count()

        return {
            "total_leads": total_leads,
            "new_leads_today": new_leads_today,
            "pending_reviews": pending_reviews,
            "active_services": active_services,
            "total_gallery_items": total_gallery,
            "published_testimonials": published_testimonials,
        }

    def get_leads_by_status(self) -> list[dict]:
        results = (
            self.db.query(Lead.status, func.count(Lead.id))
            .group_by(Lead.status)
            .all()
        )
        return [{"status": status, "count": count} for status, count in results]

    def get_monthly_leads(self, months: int = 6) -> list[dict]:
        since = datetime.now(timezone.utc) - timedelta(days=months * 30)
        results = (
            self.db.query(
                func.date_trunc("month", Lead.created_at).label("month"),
                func.count(Lead.id),
            )
            .filter(Lead.created_at >= since)
            .group_by(func.date_trunc("month", Lead.created_at))
            .order_by(func.date_trunc("month", Lead.created_at))
            .all()
        )
        return [{"month": str(month), "count": count} for month, count in results]
