from sqlalchemy.orm import Session
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.models.lead_event import LeadEvent
from app.models.user import User
from uuid import UUID


class LeadService:
    def __init__(self, db: Session):
        self.db = db

    def create_lead(self, data: dict) -> Lead:
        lead = Lead(**data)
        self.db.add(lead)
        self.db.flush()

        event = LeadEvent(
            lead_id=lead.id,
            event_type="form_submitted",
            event_metadata={"source": "main_site"},
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def get_leads(self, status: str = None, search: str = None, skip: int = 0, limit: int = 20):
        query = self.db.query(Lead)
        if status:
            query = query.filter(Lead.status == status)
        if search:
            query = query.filter(
                Lead.full_name.ilike(f"%{search}%") | Lead.phone.ilike(f"%{search}%")
            )
        total = query.count()
        leads = query.order_by(Lead.created_at.desc()).offset(skip).limit(limit).all()
        return leads, total

    def get_lead(self, lead_id: UUID) -> Lead:
        return self.db.query(Lead).filter(Lead.id == lead_id).first()

    def update_status(self, lead_id: UUID, status: str, user: User) -> Lead:
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return None
        old_status = lead.status
        lead.status = status

        event = LeadEvent(
            lead_id=lead.id,
            event_type="status_changed",
            event_metadata={"from": old_status, "to": status},
            created_by=user.id,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def add_note(self, lead_id: UUID, notes: str, user: User) -> Lead:
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return None
        lead.notes = (lead.notes or "") + f"\n[{datetime.now(timezone.utc).isoformat()}] {notes}"

        event = LeadEvent(
            lead_id=lead.id,
            event_type="note_added",
            created_by=user.id,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def delete_lead(self, lead_id: UUID) -> bool:
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return False
        self.db.delete(lead)
        self.db.commit()
        return True
