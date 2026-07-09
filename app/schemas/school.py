from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime


# --- Academic Term ---
class AcademicTermCreate(BaseModel):
    name: str
    year: str
    start_date: date
    end_date: date
    is_active: bool = False


class AcademicTermUpdate(BaseModel):
    name: Optional[str] = None
    year: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


class AcademicTermResponse(BaseModel):
    id: UUID
    name: str
    year: str
    start_date: date
    end_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- School Class ---
class SchoolClassCreate(BaseModel):
    name: str
    teacher_id: Optional[UUID] = None
    academic_term_id: UUID


class SchoolClassUpdate(BaseModel):
    name: Optional[str] = None
    teacher_id: Optional[UUID] = None
    academic_term_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class SchoolClassResponse(BaseModel):
    id: UUID
    name: str
    teacher_id: Optional[UUID]
    academic_term_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SchoolClassDetail(BaseModel):
    id: UUID
    name: str
    teacher_id: Optional[UUID]
    teacher_name: Optional[str]
    academic_term_id: UUID
    term_name: Optional[str]
    student_count: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Student ---
class StudentCreate(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    admission_number: str
    current_class_id: Optional[UUID] = None
    status: str = "active"
    date_of_admission: Optional[date] = None
    home_address: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_whatsapp: Optional[str] = None
    parent_relationship: Optional[str] = None
    emergency_contact: Optional[str] = None
    alt_emergency_contact: Optional[str] = None
    medical_conditions: Optional[str] = None
    blood_group: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    passport_photo_url: Optional[str] = None


class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    admission_number: Optional[str] = None
    current_class_id: Optional[UUID] = None
    status: Optional[str] = None
    date_of_admission: Optional[date] = None
    home_address: Optional[str] = None
    parent_name: Optional[str] = None
    parent_phone: Optional[str] = None
    parent_whatsapp: Optional[str] = None
    parent_relationship: Optional[str] = None
    emergency_contact: Optional[str] = None
    alt_emergency_contact: Optional[str] = None
    medical_conditions: Optional[str] = None
    blood_group: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    passport_photo_url: Optional[str] = None
    is_active: Optional[bool] = None


class StudentResponse(BaseModel):
    id: UUID
    first_name: str
    middle_name: Optional[str]
    last_name: str
    admission_number: str
    current_class_id: Optional[UUID]
    status: str
    date_of_admission: Optional[date]
    home_address: Optional[str]
    parent_name: Optional[str]
    parent_phone: Optional[str]
    parent_whatsapp: Optional[str]
    parent_relationship: Optional[str]
    emergency_contact: Optional[str]
    alt_emergency_contact: Optional[str]
    medical_conditions: Optional[str]
    blood_group: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[str]
    passport_photo_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StudentDetail(BaseModel):
    id: UUID
    first_name: str
    middle_name: Optional[str]
    last_name: str
    admission_number: str
    current_class_id: Optional[UUID]
    class_name: Optional[str]
    status: str
    date_of_admission: Optional[date]
    home_address: Optional[str]
    parent_name: Optional[str]
    parent_phone: Optional[str]
    parent_whatsapp: Optional[str]
    parent_relationship: Optional[str]
    emergency_contact: Optional[str]
    alt_emergency_contact: Optional[str]
    medical_conditions: Optional[str]
    blood_group: Optional[str]
    date_of_birth: Optional[date]
    gender: Optional[str]
    passport_photo_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Subject ---
class SubjectCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SubjectResponse(BaseModel):
    id: UUID
    name: str
    code: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Assessment Config ---
class AssessmentConfigCreate(BaseModel):
    name: str
    max_score: float
    sort_order: int = 0
    is_exam: bool = False


class AssessmentConfigUpdate(BaseModel):
    name: Optional[str] = None
    max_score: Optional[float] = None
    sort_order: Optional[int] = None
    is_exam: Optional[bool] = None


class AssessmentConfigResponse(BaseModel):
    id: UUID
    class_subject_id: UUID
    name: str
    max_score: float
    sort_order: int
    is_exam: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BatchAssessmentConfigCreate(BaseModel):
    class_subject_ids: list[UUID]
    configs: list[AssessmentConfigCreate]


# --- Class Subject ---
class ClassSubjectCreate(BaseModel):
    class_id: UUID
    subject_id: UUID
    teacher_id: Optional[UUID] = None
    max_score: float = 100.0


class ClassSubjectUpdate(BaseModel):
    teacher_id: Optional[UUID] = None
    max_score: Optional[float] = None


class ClassSubjectResponse(BaseModel):
    id: UUID
    class_id: UUID
    subject_id: UUID
    class_name: Optional[str]
    subject_name: Optional[str]
    subject_code: Optional[str]
    teacher_id: Optional[UUID]
    teacher_name: Optional[str]
    max_score: float
    assessment_configs: list[AssessmentConfigResponse] = []

    class Config:
        from_attributes = True


# --- Academic Record (Grades) ---
class AcademicRecordCreate(BaseModel):
    student_id: UUID
    class_subject_id: UUID
    term_id: UUID
    score: float
    max_score: float = 100.0


class AcademicRecordUpdate(BaseModel):
    score: float
    max_score: Optional[float] = None


class AcademicRecordResponse(BaseModel):
    id: UUID
    student_id: UUID
    class_subject_id: UUID
    term_id: UUID
    score: float
    max_score: float
    recorded_by: UUID
    recorded_at: datetime

    class Config:
        from_attributes = True


class GradeBatchItem(BaseModel):
    student_id: UUID
    class_subject_id: UUID
    score: float
    max_score: float = 100.0


class GradeBatchCreate(BaseModel):
    term_id: UUID
    grades: List[GradeBatchItem]


# --- Attendance ---
class AttendanceCreate(BaseModel):
    student_id: UUID
    class_id: UUID
    date: date
    status: str


class AttendanceBatchItem(BaseModel):
    student_id: UUID
    status: str


class AttendanceBatchCreate(BaseModel):
    class_id: UUID
    date: date
    records: List[AttendanceBatchItem]


class AttendanceResponse(BaseModel):
    id: UUID
    student_id: UUID
    class_id: UUID
    date: date
    status: str
    recorded_by: UUID
    recorded_at: datetime

    class Config:
        from_attributes = True


# --- Syllabus Topic ---
class SyllabusTopicCreate(BaseModel):
    class_subject_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    term_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    title: str
    content: str = ""
    week_number: Optional[int] = None
    sort_order: int = 0


class SyllabusTopicUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    week_number: Optional[int] = None
    sort_order: Optional[int] = None
    is_completed: Optional[bool] = None
    parent_id: Optional[UUID] = None


class SyllabusTopicResponse(BaseModel):
    id: UUID
    class_subject_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    term_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    title: str
    content: str
    week_number: Optional[int]
    sort_order: int
    is_completed: bool
    created_at: datetime
    updated_at: datetime
    children: list["SyllabusTopicResponse"] = []

    class Config:
        from_attributes = True


class TopicOrder(BaseModel):
    id: UUID
    sort_order: int


class SyllabusTopicMove(BaseModel):
    direction: str  # "up" or "down"


class SyllabusTopicReorder(BaseModel):
    topics: list[TopicOrder]


# --- Time Period ---
class TimePeriodCreate(BaseModel):
    name: str
    start_time: str
    end_time: str
    sort_order: int = 0


class TimePeriodUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    sort_order: Optional[int] = None


class TimePeriodResponse(BaseModel):
    id: UUID
    name: str
    start_time: str
    end_time: str
    sort_order: int

    class Config:
        from_attributes = True


# --- Timetable Entry ---
class TimetableEntryCreate(BaseModel):
    class_id: UUID
    day_of_week: int
    time_period_id: UUID
    class_subject_id: UUID
    room: Optional[str] = None


class TimetableEntryUpdate(BaseModel):
    time_period_id: Optional[UUID] = None
    class_subject_id: Optional[UUID] = None
    room: Optional[str] = None


class TimetableEntryResponse(BaseModel):
    id: UUID
    class_id: UUID
    day_of_week: int
    time_period_id: UUID
    class_subject_id: UUID
    room: Optional[str]
    time_period_name: Optional[str]
    subject_name: Optional[str]
    subject_code: Optional[str]
    teacher_name: Optional[str]

    class Config:
        from_attributes = True


# --- Dashboard ---
class TeacherClassStat(BaseModel):
    class_id: UUID
    class_name: str
    total_students: int
    total_attendance_today: int
    total_present_today: int


class TeacherDashboardResponse(BaseModel):
    classes: list[TeacherClassStat]


class SchoolDashboardResponse(BaseModel):
    total_students: int
    total_teachers: int
    teachers_count: int
    hr_count: int
    proprietor_count: int
    teachers_with_class: int
    teachers_without_class: int
    total_classes: int
    total_classes_active: int
    attendance_percentage: float
    students_with_class: int
    students_without_class: int
    students_by_class: List[dict]
    attendance_by_day: List[dict]


# --- Grading Scale ---
class GradingScaleCreate(BaseModel):
    grade: str
    min_score: float
    max_score: float
    remark: str = ""


class GradingScaleUpdate(BaseModel):
    grade: Optional[str] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    remark: Optional[str] = None
    is_active: Optional[bool] = None


class GradingScaleResponse(BaseModel):
    id: UUID
    grade: str
    min_score: float
    max_score: float
    remark: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- Report Card ---
class ReportCardSubject(BaseModel):
    subject_name: str
    subject_code: str
    score: float
    max_score: float
    grade: str = ""
    remark: str = ""
    ca_scores: dict[str, float] = {}
    exam_score: Optional[float] = None
    ca_total: float = 0.0
    exam_max: float = 0.0
    ca_max: float = 0.0
    is_assessment_based: bool = False
    comment: str = ""


class ReportCardResponse(BaseModel):
    student_id: UUID
    student_name: str
    admission_number: str
    class_name: str
    term_name: str
    term_year: str
    subjects: list[ReportCardSubject]
    total_score: float
    total_max_score: float
    average: float
    position: int = 0
    total_students: int = 0
    # Affective Domain
    times_school_opened: Optional[int] = None
    times_present: Optional[int] = None
    times_absent: Optional[int] = None
    punctuality: Optional[str] = None
    neatness: Optional[str] = None
    leadership: Optional[str] = None
    demeanour: Optional[str] = None
    literacy: Optional[str] = None
    sporting: Optional[str] = None
    cultural: Optional[str] = None
    # Remarks
    proprietors_remarks: Optional[str] = None
    teacher_remark: Optional[str] = None
    # School Fees
    tuition_fee: Optional[float] = None
    other_fees: Optional[float] = None
    total_fees: Optional[float] = None
    # Dates
    next_term_begin: Optional[date] = None
    # Comments
    class_teacher_comment: Optional[str] = None
    head_teacher_comment: Optional[str] = None


class ReportCardExtraSave(BaseModel):
    times_school_opened: Optional[int] = None
    times_present: Optional[int] = None
    times_absent: Optional[int] = None
    punctuality: Optional[str] = None
    neatness: Optional[str] = None
    leadership: Optional[str] = None
    demeanour: Optional[str] = None
    literacy: Optional[str] = None
    sporting: Optional[str] = None
    cultural: Optional[str] = None
    proprietors_remarks: Optional[str] = None
    teacher_remark: Optional[str] = None
    tuition_fee: Optional[float] = None
    other_fees: Optional[float] = None
    total_fees: Optional[float] = None
    next_term_begin: Optional[date] = None
    class_teacher_comment: Optional[str] = None
    head_teacher_comment: Optional[str] = None


# --- Transcript ---
class TranscriptTerm(BaseModel):
    term_id: UUID
    term_name: str
    year: str
    subjects: list[ReportCardSubject]
    total_score: float
    total_max_score: float
    average: float


class TranscriptResponse(BaseModel):
    student_id: UUID
    student_name: str
    admission_number: str
    terms: list[TranscriptTerm]


# --- Outlist ---
class OutlistStudent(BaseModel):
    id: UUID
    first_name: str
    middle_name: Optional[str]
    last_name: str
    admission_number: str
    status: str
    class_name: Optional[str]
    date_of_admission: Optional[date]
    parent_name: Optional[str]
    parent_phone: Optional[str]
    emergency_contact: Optional[str]


class OutlistResponse(BaseModel):
    students: list[OutlistStudent]


# --- Grading Info (for frontend to compute locally) ---
class GradingInfoResponse(BaseModel):
    scales: list[GradingScaleResponse]


# --- Assessment Score ---
class AssessmentScoreCreate(BaseModel):
    student_id: UUID
    class_subject_id: UUID
    term_id: UUID
    assessment_config_id: UUID
    score: float


class AssessmentScoreBatchItem(BaseModel):
    student_id: UUID
    class_subject_id: UUID
    assessment_config_id: UUID
    score: float


class AssessmentScoreBatchCreate(BaseModel):
    term_id: UUID
    scores: list[AssessmentScoreBatchItem]


class AssessmentScoreResponse(BaseModel):
    id: UUID
    student_id: UUID
    class_subject_id: UUID
    term_id: UUID
    assessment_config_id: UUID
    score: float
    recorded_by: UUID
    recorded_at: datetime

    class Config:
        from_attributes = True
