from sqlalchemy.orm import Session
from app.models.page_section import PageSection


class PageSectionService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[PageSection]:
        return self.db.query(PageSection).order_by(PageSection.display_order).all()

    def update(self, name: str, data: dict) -> PageSection | None:
        section = self.db.query(PageSection).filter(PageSection.name == name).first()
        if not section:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(section, key, value)
        self.db.commit()
        self.db.refresh(section)
        return section
