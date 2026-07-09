from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as SQLUuid
from app.models.base import Base


class SyllabusDocument(Base):
    __tablename__ = "syllabus_documents"

    id = Column(SQLUuid, primary_key=True, default=uuid4)
    class_subject_id = Column(SQLUuid, ForeignKey("class_subjects.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    file_url = Column(String(512), nullable=False)
    original_filename = Column(String(255))
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
