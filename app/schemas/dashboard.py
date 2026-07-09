from pydantic import BaseModel
from typing import Optional


class DashboardMetrics(BaseModel):
    total_leads: int
    new_leads_today: int
    pending_reviews: int
    active_services: int
    total_gallery_items: int
    published_testimonials: int


class LeadStatusCount(BaseModel):
    status: str
    count: int


class MonthlyLeads(BaseModel):
    month: str
    count: int


class DashboardResponse(BaseModel):
    metrics: DashboardMetrics
    leads_by_status: list[LeadStatusCount]
    monthly_leads: list[MonthlyLeads]
