from sqlalchemy import Column, String, ForeignKey, Integer, Numeric, Text, Date, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.db.session import Base
from app.models.base import TimestampMixin


class ReportCardExtra(TimestampMixin, Base):
    __tablename__ = "report_card_extras"

    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    term_id = Column(UUID(as_uuid=True), ForeignKey("academic_terms.id"), nullable=False)

    # Affective Domain - Punctuality & Regularity
    times_school_opened = Column(Integer, nullable=True)
    times_present = Column(Integer, nullable=True)
    times_absent = Column(Integer, nullable=True)

    # Affective Domain - Character traits
    punctuality = Column(String(50), nullable=True)
    neatness = Column(String(50), nullable=True)
    leadership = Column(String(50), nullable=True)
    demeanour = Column(String(50), nullable=True)

    # Skills
    literacy = Column(String(50), nullable=True)
    sporting = Column(String(50), nullable=True)
    cultural = Column(String(50), nullable=True)

    # Proprietor / Teacher remarks
    proprietors_remarks = Column(Text, nullable=True)
    teacher_remark = Column(Text, nullable=True)

    # School Fees
    tuition_fee = Column(Numeric(10, 2), nullable=True)
    other_fees = Column(Numeric(10, 2), nullable=True)
    total_fees = Column(Numeric(10, 2), nullable=True)

    # Dates
    next_term_begin = Column(Date, nullable=True)

    # Comments
    class_teacher_comment = Column(Text, nullable=True)
    head_teacher_comment = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("student_id", "term_id", name="uq_student_term_extra"),
    )
