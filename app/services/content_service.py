import os
from sqlalchemy.orm import Session
from app.models.site_content import SiteContent
from uuid import UUID

LOGO_SVG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "uploads", "logo.svg",
)


def _write_logo_svg_file(svg: str):
    os.makedirs(os.path.dirname(LOGO_SVG_PATH), exist_ok=True)
    with open(LOGO_SVG_PATH, "w", encoding="utf-8") as f:
        f.write(svg)


class ContentService:
    def __init__(self, db: Session):
        self.db = db

    def create_content(self, data: dict) -> SiteContent:
        content = SiteContent(**data)
        self.db.add(content)
        self.db.commit()
        self.db.refresh(content)
        if data.get("field_key") == "logo_svg" and data.get("field_value"):
            _write_logo_svg_file(data["field_value"])
        return content

    def get_section_content(self, section: str) -> list[SiteContent]:
        return (
            self.db.query(SiteContent)
            .filter(SiteContent.section == section, SiteContent.is_active == True)
            .all()
        )

    def get_all_content(self) -> list[SiteContent]:
        return self.db.query(SiteContent).order_by(SiteContent.section, SiteContent.field_key).all()

    def update_content(self, content_id: UUID, data: dict) -> SiteContent:
        content = self.db.query(SiteContent).filter(SiteContent.id == content_id).first()
        if not content:
            return None
        for key, value in data.items():
            if value is not None:
                setattr(content, key, value)
        self.db.commit()
        self.db.refresh(content)
        if content.field_key == "logo_svg" and content.field_value:
            _write_logo_svg_file(content.field_value)
        return content

    def delete_content(self, content_id: UUID) -> bool:
        content = self.db.query(SiteContent).filter(SiteContent.id == content_id).first()
        if not content:
            return False
        self.db.delete(content)
        self.db.commit()
        return True

    def bulk_update(self, updates: list[dict]) -> list[SiteContent]:
        results = []
        for update in updates:
            content = self.update_content(update["id"], update)
            if content:
                results.append(content)
        return results
