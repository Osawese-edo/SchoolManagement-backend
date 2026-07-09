import os
import secrets
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user, require_permission
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.permissions import (
    ATTENDANCE_SUBMIT, ATTENDANCE_VIEW,
    GRADES_SUBMIT, GRADES_VIEW,
    STUDENTS_VIEW, STUDENTS_CREATE, STUDENTS_EDIT, STUDENTS_DELETE,
    CLASSES_VIEW, CLASSES_CREATE, CLASSES_EDIT, CLASSES_DELETE,
    SUBJECTS_VIEW, SUBJECTS_CREATE, SUBJECTS_EDIT, SUBJECTS_DELETE,
    STAFF_VIEW, STAFF_CREATE, STAFF_EDIT, STAFF_DELETE,
    TERMS_VIEW, TERMS_MANAGE,
    CURRICULUM_VIEW, CURRICULUM_MANAGE,
    SYLLABUS_VIEW, SYLLABUS_MANAGE,
    TIMETABLE_VIEW, TIMETABLE_MANAGE,
    REPORTS_VIEW,
    DASHBOARD_VIEW,
    GRADING_MANAGE,
)
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.academic_record import AcademicRecord
from app.models.academic_term import AcademicTerm
from app.models.assessment_config import AssessmentConfig
from app.models.assessment_score import AssessmentScore
from app.models.attendance import Attendance
from app.models.class_subject import ClassSubject
from app.models.grading_scale import GradingScale
from app.models.report_card_extra import ReportCardExtra
from app.models.school_class import SchoolClass
from app.models.staff import Staff
from app.models.student import Student
from app.models.subject import Subject
from app.models.syllabus_document import SyllabusDocument
from app.models.syllabus_topic import SyllabusTopic
from app.models.time_period import TimePeriod
from app.models.time_table_entry import TimeTableEntry
from app.models.user import User
from app.schemas.school import (
    AcademicTermCreate, AcademicTermUpdate, AcademicTermResponse,
    SchoolClassCreate, SchoolClassUpdate, SchoolClassResponse, SchoolClassDetail,
    StudentCreate, StudentUpdate, StudentResponse, StudentDetail,
    SubjectCreate, SubjectUpdate, SubjectResponse,
    ClassSubjectCreate, ClassSubjectUpdate, ClassSubjectResponse,
    AcademicRecordCreate, AcademicRecordUpdate, AcademicRecordResponse,
    GradeBatchCreate,
    AttendanceCreate, AttendanceBatchCreate, AttendanceResponse,
    TeacherDashboardResponse, TeacherClassStat, SchoolDashboardResponse,
    SyllabusTopicCreate, SyllabusTopicUpdate, SyllabusTopicResponse,
    SyllabusTopicMove, SyllabusTopicReorder, TopicOrder,
    TimePeriodCreate, TimePeriodUpdate, TimePeriodResponse,
    TimetableEntryCreate, TimetableEntryUpdate, TimetableEntryResponse,
    GradingScaleCreate, GradingScaleUpdate, GradingScaleResponse,
    ReportCardResponse, ReportCardSubject, ReportCardExtraSave,
    TranscriptResponse, TranscriptTerm,
    OutlistResponse, OutlistStudent,
    GradingInfoResponse,
    AssessmentConfigCreate, AssessmentConfigUpdate, AssessmentConfigResponse,
    BatchAssessmentConfigCreate,
    AssessmentScoreCreate, AssessmentScoreBatchItem, AssessmentScoreBatchCreate, AssessmentScoreResponse,
)
from app.services.log_helper import log_action
from app.services.upload_service import UPLOAD_DIR, UploadService, validate_magic_bytes

router = APIRouter()

from app.api.school.staff_routes import router as staff_router
router.include_router(staff_router)


# ─── Helper ────────────────────────────────────────────────────────────────

def get_user_teacher_id(user: User, db: Session) -> UUID | None:
    """Return a teacher's assigned class ID, or None if user has dashboard view_all."""
    from app.core.permissions import has_permission, DASHBOARD_VIEW
    if has_permission(user, DASHBOARD_VIEW) and user.role != "teacher":
        return None
    staff = db.query(Staff).filter(Staff.user_id == user.id).first()
    if not staff:
        return None
    if user.role == "teacher":
        return None
    cls = db.query(SchoolClass).filter(SchoolClass.teacher_id == staff.id).first()
    return cls.id if cls else None


def get_staff_for_user(user: User, db: Session) -> Staff | None:
    return db.query(Staff).filter(Staff.user_id == user.id).first()


def student_to_detail(s: Student) -> StudentDetail:
    return StudentDetail(
        id=s.id,
        first_name=s.first_name,
        middle_name=s.middle_name,
        last_name=s.last_name,
        admission_number=s.admission_number,
        current_class_id=s.current_class_id,
        class_name=s.current_class_rel.name if s.current_class_rel else None,
        status=s.status,
        date_of_admission=s.date_of_admission,
        home_address=s.home_address,
        parent_name=s.parent_name,
        parent_phone=s.parent_phone,
        parent_whatsapp=s.parent_whatsapp,
        parent_relationship=s.parent_relationship,
        emergency_contact=s.emergency_contact,
        alt_emergency_contact=s.alt_emergency_contact,
        medical_conditions=s.medical_conditions,
        blood_group=s.blood_group,
        date_of_birth=s.date_of_birth,
        gender=s.gender,
        passport_photo_url=s.passport_photo_url,
        is_active=s.is_active,
        created_at=s.created_at,
    )


# ─── Dashboard ────────────────────────────────────────────────────────────

@router.get("/dashboard")
@limiter.limit("120/minute")
def get_school_dashboard(
    request: Request,
    current_user: User = Depends(require_permission(DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    user = current_user
    if user.role == "teacher":
        staff = get_staff_for_user(user, db)
        today = date.today()
        if staff:
            classes = db.query(SchoolClass).filter(
                SchoolClass.teacher_id == staff.id
            ).order_by(SchoolClass.name).all()

            student_counts = dict(
                db.query(
                    Student.current_class_id,
                    func.count(Student.id)
                ).filter(
                    Student.current_class_id.in_([c.id for c in classes]),
                    Student.is_active == True
                ).group_by(Student.current_class_id).all()
            )

            class_ids = [c.id for c in classes]
            attendance_counts = db.query(
                Attendance.class_id,
                Attendance.status,
                func.count(Attendance.id)
            ).filter(
                Attendance.class_id.in_(class_ids),
                Attendance.date == today
            ).group_by(Attendance.class_id, Attendance.status).all()

            att_map = {}
            for cid, status, cnt in attendance_counts:
                key = str(cid)
                if key not in att_map:
                    att_map[key] = {"total": 0, "present": 0}
                att_map[key]["total"] += cnt
                if status == "PRESENT":
                    att_map[key]["present"] += cnt

            classes_list = []
            for cls in classes:
                cid_str = str(cls.id)
                ac = att_map.get(cid_str, {"total": 0, "present": 0})
                classes_list.append(TeacherClassStat(
                    class_id=cls.id, class_name=cls.name,
                    total_students=student_counts.get(cls.id, 0),
                    total_attendance_today=ac["total"],
                    total_present_today=ac["present"],
                ))
            return TeacherDashboardResponse(classes=classes_list)
        return TeacherDashboardResponse(classes=[])

    total_students = db.query(func.count(Student.id)).filter(Student.is_active == True).scalar() or 0

    teachers_count = db.query(func.count(Staff.id)).filter(
        Staff.role == "teacher", Staff.is_active == True
    ).scalar() or 0
    hr_count = db.query(func.count(Staff.id)).filter(
        Staff.role == "hr", Staff.is_active == True
    ).scalar() or 0
    proprietor_count = db.query(func.count(Staff.id)).filter(
        Staff.role == "proprietor", Staff.is_active == True
    ).scalar() or 0

    # Teachers with/without class assignment
    teachers_with_class = db.query(func.count(Staff.id)).filter(
        Staff.role == "teacher", Staff.is_active == True,
        Staff.id.in_(db.query(SchoolClass.teacher_id).filter(SchoolClass.teacher_id.isnot(None)))
    ).scalar() or 0
    teachers_without_class = max(0, teachers_count - teachers_with_class)

    if current_user.role == "hr":
        total_teachers = teachers_count
    elif current_user.role == "proprietor":
        total_teachers = teachers_count + hr_count
    else:
        total_teachers = teachers_count + hr_count + proprietor_count
    total_classes = db.query(func.count(SchoolClass.id)).scalar() or 0
    active_classes = db.query(func.count(SchoolClass.id)).filter(SchoolClass.is_active == True).scalar() or 0

    today = date.today()
    students_with_class = db.query(func.count(Student.id)).filter(
        Student.current_class_id.isnot(None), Student.is_active == True
    ).scalar() or 0
    students_without_class = db.query(func.count(Student.id)).filter(
        Student.current_class_id.is_(None), Student.is_active == True
    ).scalar() or 0

    total_attendance = db.query(func.count(Attendance.id)).filter(Attendance.date == today).scalar() or 0
    present_attendance = db.query(func.count(Attendance.id)).filter(
        Attendance.date == today, Attendance.status == "PRESENT"
    ).scalar() or 0
    att_pct = (present_attendance / total_attendance * 100) if total_attendance > 0 else 0.0

    by_class = db.query(
        SchoolClass.name,
        func.count(Student.id).label("count"),
    ).outerjoin(Student, Student.current_class_id == SchoolClass.id
    ).filter(Student.is_active == True).group_by(SchoolClass.id, SchoolClass.name).all()

    by_day = db.query(
        Attendance.date,
        func.count(Attendance.id).label("count"),
    ).filter(
        Attendance.date >= date.today() - timedelta(days=30)
    ).group_by(Attendance.date).order_by(Attendance.date).all()

    return SchoolDashboardResponse(
        total_students=total_students,
        total_teachers=total_teachers,
        teachers_count=teachers_count,
        hr_count=hr_count,
        proprietor_count=proprietor_count,
        teachers_with_class=teachers_with_class,
        teachers_without_class=teachers_without_class,
        total_classes=total_classes,
        total_classes_active=active_classes,
        attendance_percentage=round(att_pct, 1),
        students_with_class=students_with_class,
        students_without_class=students_without_class,
        students_by_class=[{"name": r[0], "count": r[1]} for r in by_class],
        attendance_by_day=[{"date": str(r[0]), "count": r[1]} for r in by_day],
    )


# ─── Academic Terms ────────────────────────────────────────────────────────

@router.get("/terms", response_model=list[AcademicTermResponse])
@limiter.limit("120/minute")
def list_terms(
    request: Request,
    current_user: User = Depends(require_permission(TERMS_VIEW)),
    db: Session = Depends(get_db),
):
    return db.query(AcademicTerm).order_by(AcademicTerm.year.desc(), AcademicTerm.start_date.desc()).limit(500).all()


@router.post("/terms", response_model=AcademicTermResponse, status_code=201)
@limiter.limit("30/minute")
def create_term(
    request: Request,
    data: AcademicTermCreate,
    current_user: User = Depends(require_permission(TERMS_MANAGE)),
    db: Session = Depends(get_db),
):
    if data.is_active:
        db.query(AcademicTerm).filter(AcademicTerm.is_active == True).update({"is_active": False})
    term = AcademicTerm(**data.model_dump())
    db.add(term)
    db.commit()
    db.refresh(term)
    log_action(db, current_user, "Created term", "term", str(term.id))
    return term


@router.patch("/terms/{term_id}", response_model=AcademicTermResponse)
@limiter.limit("30/minute")
def update_term(
    request: Request,
    term_id: UUID,
    data: AcademicTermUpdate,
    current_user: User = Depends(require_permission(TERMS_MANAGE)),
    db: Session = Depends(get_db),
):
    term = db.query(AcademicTerm).filter(AcademicTerm.id == term_id).first()
    if not term:
        raise NotFoundException("Term not found")
    if data.is_active:
        db.query(AcademicTerm).filter(AcademicTerm.is_active == True).update({"is_active": False})
    for key, val in data.model_dump(exclude_none=True).items():
        setattr(term, key, val)
    db.commit()
    log_action(db, current_user, "Updated term", "term", str(term_id))
    db.refresh(term)
    return term


@router.delete("/terms/{term_id}")
@limiter.limit("30/minute")
def delete_term(
    request: Request,
    term_id: UUID,
    current_user: User = Depends(require_permission(TERMS_MANAGE)),
    db: Session = Depends(get_db),
):
    term = db.query(AcademicTerm).filter(AcademicTerm.id == term_id).first()
    if not term:
        raise NotFoundException("Term not found")

    classes_count = db.query(func.count(SchoolClass.id)).filter(
        SchoolClass.academic_term_id == term_id
    ).scalar() or 0
    if classes_count > 0:
        raise ConflictException(
            f"Cannot delete term '{term.name}'. It is linked to {classes_count} class(es). Remove or reassign the classes first."
        )

    db.delete(term)
    db.commit()
    log_action(db, current_user, "Deleted term", "term", str(term_id))
    return {"message": "Term deleted"}


# ─── Classes ───────────────────────────────────────────────────────────────

@router.get("/classes", response_model=list[SchoolClassDetail])
@limiter.limit("120/minute")
def list_classes(
    request: Request,
    current_user: User = Depends(require_permission(CLASSES_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(SchoolClass).options(
        joinedload(SchoolClass.teacher_rel), joinedload(SchoolClass.term_rel)
    )
    tcid = get_user_teacher_id(current_user, db)
    if tcid:
        query = query.filter(SchoolClass.id == tcid)
    elif current_user.role == "teacher":
        staff = get_staff_for_user(current_user, db)
        if staff:
            subject_class_ids = db.query(ClassSubject.class_id).filter(
                ClassSubject.teacher_id == staff.id
            ).distinct()
            query = query.filter(
                (SchoolClass.teacher_id == staff.id) |
                (SchoolClass.id.in_(subject_class_ids))
            )

    classes = query.order_by(SchoolClass.created_at.asc()).limit(500).all()
    result = []
    for cls in classes:
        student_count = db.query(func.count(Student.id)).filter(
            Student.current_class_id == cls.id, Student.is_active == True
        ).scalar() or 0
        result.append(SchoolClassDetail(
            id=cls.id,
            name=cls.name,
            teacher_id=cls.teacher_id,
            teacher_name=f"{cls.teacher_rel.first_name} {cls.teacher_rel.last_name}" if cls.teacher_rel else None,
            academic_term_id=cls.academic_term_id,
            term_name=cls.term_rel.name if cls.term_rel else None,
            student_count=student_count,
            is_active=cls.is_active,
            created_at=cls.created_at,
        ))
    return result


@router.post("/classes", response_model=SchoolClassResponse, status_code=201)
@limiter.limit("30/minute")
def create_class(
    request: Request,
    data: SchoolClassCreate,
    current_user: User = Depends(require_permission(CLASSES_CREATE)),
    db: Session = Depends(get_db),
):
    cls = SchoolClass(**data.model_dump())
    db.add(cls)
    db.commit()
    db.refresh(cls)
    log_action(db, current_user, "Created class", "class", str(cls.id))
    return cls


@router.patch("/classes/{class_id}", response_model=SchoolClassResponse)
@limiter.limit("30/minute")
def update_class(
    request: Request,
    class_id: UUID,
    data: SchoolClassUpdate,
    current_user: User = Depends(require_permission(CLASSES_EDIT)),
    db: Session = Depends(get_db),
):
    cls = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not cls:
        raise NotFoundException("Class not found")
    for key, val in data.model_dump(exclude_none=True).items():
        setattr(cls, key, val)
    db.commit()
    log_action(db, current_user, "Updated class", "class", str(class_id))
    db.refresh(cls)
    return cls


@router.delete("/classes/{class_id}")
@limiter.limit("30/minute")
def delete_class(
    request: Request,
    class_id: UUID,
    current_user: User = Depends(require_permission(CLASSES_DELETE)),
    db: Session = Depends(get_db),
):
    cls = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not cls:
        raise NotFoundException("Class not found")
    db.query(Student).filter(Student.current_class_id == class_id).update({"current_class_id": None})
    db.delete(cls)
    db.commit()
    log_action(db, current_user, "Deleted class", "class", str(class_id))
    return {"message": "Class deleted"}


# ─── Students ──────────────────────────────────────────────────────────────

@router.get("/students", response_model=list[StudentDetail])
@limiter.limit("120/minute")
def list_students(
    request: Request,
    class_id: UUID | None = Query(None),
    search: str | None = Query(None),
    current_user: User = Depends(require_permission(STUDENTS_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Student).outerjoin(SchoolClass, Student.current_class_id == SchoolClass.id)

    tcid = get_user_teacher_id(current_user, db)
    if tcid:
        query = query.filter(Student.current_class_id == tcid)
    elif current_user.role == "teacher":
        staff = get_staff_for_user(current_user, db)
        if staff:
            subject_class_ids = db.query(ClassSubject.class_id).filter(
                ClassSubject.teacher_id == staff.id
            ).distinct()
            query = query.filter(
                (SchoolClass.teacher_id == staff.id) |
                (SchoolClass.id.in_(subject_class_ids))
            )

    if class_id:
        query = query.filter(Student.current_class_id == class_id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            Student.first_name.ilike(pattern) |
            Student.last_name.ilike(pattern) |
            Student.admission_number.ilike(pattern)
        )

    students = query.order_by(Student.created_at.asc()).limit(500).all()
    return [student_to_detail(s) for s in students]


@router.post("/students", response_model=StudentDetail, status_code=201)
@limiter.limit("30/minute")
def create_student(
    request: Request,
    data: StudentCreate,
    current_user: User = Depends(require_permission(STUDENTS_CREATE)),
    db: Session = Depends(get_db),
):
    existing = db.query(Student).filter(Student.admission_number == data.admission_number).first()
    if existing:
        raise ConflictException("Admission number already exists")
    student = Student(**data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    log_action(db, current_user, "Created student", "student", str(student.id), {"name": f"{student.first_name} {student.last_name}"})
    return student_to_detail(student)


@router.get("/students/{student_id}", response_model=StudentDetail)
@limiter.limit("120/minute")
def get_student(
    request: Request,
    student_id: UUID,
    current_user: User = Depends(require_permission(STUDENTS_VIEW)),
    db: Session = Depends(get_db),
):
    student = db.query(Student).options(
        joinedload(Student.current_class_rel)
    ).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundException("Student not found")
    return student_to_detail(student)


@router.patch("/students/{student_id}", response_model=StudentDetail)
@limiter.limit("30/minute")
def update_student(
    request: Request,
    student_id: UUID,
    data: StudentUpdate,
    current_user: User = Depends(require_permission(STUDENTS_EDIT)),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundException("Student not found")
    for key, val in data.model_dump(exclude_none=True).items():
        setattr(student, key, val)
    db.commit()
    log_action(db, current_user, "Updated student", "student", str(student_id))
    db.refresh(student)
    return student_to_detail(student)


@router.delete("/students/{student_id}")
@limiter.limit("30/minute")
def delete_student(
    request: Request,
    student_id: UUID,
    current_user: User = Depends(require_permission(STUDENTS_DELETE)),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundException("Student not found")
    db.delete(student)
    db.commit()
    log_action(db, current_user, "Deleted student", "student", str(student_id))
    return {"message": "Student deleted"}


# ─── Subjects ──────────────────────────────────────────────────────────────

@router.get("/subjects", response_model=list[SubjectResponse])
@limiter.limit("120/minute")
def list_subjects(
    request: Request,
    current_user: User = Depends(require_permission(SUBJECTS_VIEW)),
    db: Session = Depends(get_db),
):
    return db.query(Subject).order_by(Subject.created_at.asc()).limit(500).all()


@router.post("/subjects", response_model=SubjectResponse, status_code=201)
@limiter.limit("30/minute")
def create_subject(
    request: Request,
    data: SubjectCreate,
    current_user: User = Depends(require_permission(SUBJECTS_CREATE)),
    db: Session = Depends(get_db),
):
    existing = db.query(Subject).filter(
        (Subject.code == data.code) | (Subject.name == data.name)
    ).first()
    if existing:
        raise ConflictException("Subject with this code or name already exists")
    subject = Subject(**data.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    log_action(db, current_user, "Created subject", "subject", str(subject.id), {"name": subject.name})
    return subject


@router.patch("/subjects/{subject_id}", response_model=SubjectResponse)
@limiter.limit("30/minute")
def update_subject(
    request: Request,
    subject_id: UUID,
    data: SubjectUpdate,
    current_user: User = Depends(require_permission(SUBJECTS_EDIT)),
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise NotFoundException("Subject not found")
    for key, val in data.model_dump(exclude_none=True).items():
        setattr(subject, key, val)
    db.commit()
    log_action(db, current_user, "Updated subject", "subject", str(subject_id))
    db.refresh(subject)
    return subject


@router.delete("/subjects/{subject_id}")
@limiter.limit("30/minute")
def delete_subject(
    request: Request,
    subject_id: UUID,
    current_user: User = Depends(require_permission(SUBJECTS_DELETE)),
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise NotFoundException("Subject not found")
    db.delete(subject)
    db.commit()
    log_action(db, current_user, "Deleted subject", "subject", str(subject_id))
    return {"message": "Subject deleted"}


# ─── Class-Subject Mapping ─────────────────────────────────────────────────

@router.get("/class-subjects", response_model=list[ClassSubjectResponse])
@limiter.limit("120/minute")
def list_class_subjects(
    request: Request,
    class_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission(CURRICULUM_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(ClassSubject).options(
        joinedload(ClassSubject.subject_rel), joinedload(ClassSubject.teacher_rel), joinedload(ClassSubject.class_rel)
    )
    if class_id:
        query = query.filter(ClassSubject.class_id == class_id)
    tcid = get_user_teacher_id(current_user, db)
    if tcid:
        query = query.filter(ClassSubject.class_id == tcid)
    elif current_user.role == "teacher":
        staff = get_staff_for_user(current_user, db)
        if staff:
            query = query.join(SchoolClass, ClassSubject.class_id == SchoolClass.id)
            query = query.filter(
                (SchoolClass.teacher_id == staff.id) |
                (ClassSubject.teacher_id == staff.id)
            )
    results = query.order_by(ClassSubject.created_at.asc()).limit(500).all()

    def config_to_response(c):
        return AssessmentConfigResponse(
            id=c.id, class_subject_id=c.class_subject_id, name=c.name,
            max_score=c.max_score, sort_order=c.sort_order, is_exam=c.is_exam,
            created_at=c.created_at, updated_at=c.updated_at,
        )

    return [
        ClassSubjectResponse(
            id=cs.id,
            class_id=cs.class_id,
            subject_id=cs.subject_id,
            class_name=cs.class_rel.name if cs.class_rel else None,
            subject_name=cs.subject_rel.name if cs.subject_rel else None,
            subject_code=cs.subject_rel.code if cs.subject_rel else None,
            teacher_id=cs.teacher_id,
            teacher_name=f"{cs.teacher_rel.first_name} {cs.teacher_rel.last_name}" if cs.teacher_rel else None,
            max_score=cs.max_score,
            assessment_configs=[config_to_response(c) for c in (cs.assessment_configs or [])],
        )
        for cs in results
    ]


@router.post("/class-subjects", response_model=ClassSubjectResponse, status_code=201)
@limiter.limit("30/minute")
def create_class_subject(
    request: Request,
    data: ClassSubjectCreate,
    current_user: User = Depends(require_permission(CURRICULUM_MANAGE)),
    db: Session = Depends(get_db),
):
    cs = ClassSubject(**data.model_dump())
    db.add(cs)
    db.commit()
    db.refresh(cs)
    log_action(db, current_user, "Assigned subject to class", "curriculum", str(cs.id))
    cs = db.query(ClassSubject).options(
        joinedload(ClassSubject.subject_rel), joinedload(ClassSubject.teacher_rel), joinedload(ClassSubject.class_rel)
    ).filter(ClassSubject.id == cs.id).first()
    return ClassSubjectResponse(
        id=cs.id,
        class_id=cs.class_id,
        subject_id=cs.subject_id,
        class_name=cs.class_rel.name if cs.class_rel else None,
        subject_name=cs.subject_rel.name if cs.subject_rel else None,
        subject_code=cs.subject_rel.code if cs.subject_rel else None,
        teacher_id=cs.teacher_id,
        teacher_name=f"{cs.teacher_rel.first_name} {cs.teacher_rel.last_name}" if cs.teacher_rel else None,
        max_score=cs.max_score,
    )


@router.patch("/class-subjects/{cs_id}", response_model=ClassSubjectResponse)
@limiter.limit("30/minute")
def update_class_subject(
    request: Request,
    cs_id: UUID,
    data: ClassSubjectUpdate,
    current_user: User = Depends(require_permission(CURRICULUM_MANAGE)),
    db: Session = Depends(get_db),
):
    cs = db.query(ClassSubject).options(
        joinedload(ClassSubject.subject_rel), joinedload(ClassSubject.teacher_rel), joinedload(ClassSubject.class_rel)
    ).filter(ClassSubject.id == cs_id).first()
    if not cs:
        raise NotFoundException("Class-Subject mapping not found")
    for key, val in data.model_dump(exclude_none=True).items():
        setattr(cs, key, val)
    db.commit()
    log_action(db, current_user, "Updated class-subject", "curriculum", str(cs_id))
    db.refresh(cs)
    return ClassSubjectResponse(
        id=cs.id,
        class_id=cs.class_id,
        subject_id=cs.subject_id,
        class_name=cs.class_rel.name if cs.class_rel else None,
        subject_name=cs.subject_rel.name if cs.subject_rel else None,
        subject_code=cs.subject_rel.code if cs.subject_rel else None,
        teacher_id=cs.teacher_id,
        teacher_name=f"{cs.teacher_rel.first_name} {cs.teacher_rel.last_name}" if cs.teacher_rel else None,
        max_score=cs.max_score,
    )


@router.delete("/class-subjects/{cs_id}")
@limiter.limit("30/minute")
def delete_class_subject(
    request: Request,
    cs_id: UUID,
    current_user: User = Depends(require_permission(CURRICULUM_MANAGE)),
    db: Session = Depends(get_db),
):
    cs = db.query(ClassSubject).filter(ClassSubject.id == cs_id).first()
    if not cs:
        raise NotFoundException("Class-Subject mapping not found")
    db.delete(cs)
    db.commit()
    log_action(db, current_user, "Removed subject from class", "curriculum", str(cs_id))
    return {"message": "Class-Subject mapping deleted"}


# ─── Assessment Config ─────────────────────────────────────────────────────

def _config_to_response(c: AssessmentConfig) -> AssessmentConfigResponse:
    return AssessmentConfigResponse(
        id=c.id, class_subject_id=c.class_subject_id, name=c.name,
        max_score=c.max_score, sort_order=c.sort_order, is_exam=c.is_exam,
        created_at=c.created_at, updated_at=c.updated_at,
    )


@router.get("/class-subjects/{cs_id}/assessment-configs", response_model=list[AssessmentConfigResponse])
@limiter.limit("120/minute")
def list_assessment_configs(
    request: Request,
    cs_id: UUID,
    current_user: User = Depends(require_permission(CURRICULUM_VIEW)),
    db: Session = Depends(get_db),
):
    configs = db.query(AssessmentConfig).filter(
        AssessmentConfig.class_subject_id == cs_id
    ).order_by(AssessmentConfig.sort_order).limit(500).all()
    return [_config_to_response(c) for c in configs]


@router.post("/class-subjects/{cs_id}/assessment-configs", response_model=AssessmentConfigResponse, status_code=201)
@limiter.limit("30/minute")
def create_assessment_config(
    request: Request,
    cs_id: UUID,
    data: AssessmentConfigCreate,
    current_user: User = Depends(require_permission(CURRICULUM_MANAGE)),
    db: Session = Depends(get_db),
):
    cs = db.query(ClassSubject).filter(ClassSubject.id == cs_id).first()
    if not cs:
        raise NotFoundException("Class-Subject mapping not found")
    config = AssessmentConfig(class_subject_id=cs_id, **data.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    log_action(db, current_user, "Created assessment config", "assessment_config", str(config.id))
    return _config_to_response(config)


@router.patch("/assessment-configs/{config_id}", response_model=AssessmentConfigResponse)
@limiter.limit("30/minute")
def update_assessment_config(
    request: Request,
    config_id: UUID,
    data: AssessmentConfigUpdate,
    current_user: User = Depends(require_permission(CURRICULUM_MANAGE)),
    db: Session = Depends(get_db),
):
    config = db.query(AssessmentConfig).filter(AssessmentConfig.id == config_id).first()
    if not config:
        raise NotFoundException("Assessment config not found")
    for key, val in data.model_dump(exclude_none=True).items():
        setattr(config, key, val)
    db.commit()
    log_action(db, current_user, "Updated assessment config", "assessment_config", str(config_id))
    db.refresh(config)
    return _config_to_response(config)


@router.delete("/assessment-configs/{config_id}")
@limiter.limit("30/minute")
def delete_assessment_config(
    request: Request,
    config_id: UUID,
    current_user: User = Depends(require_permission(CURRICULUM_MANAGE)),
    db: Session = Depends(get_db),
):
    config = db.query(AssessmentConfig).filter(AssessmentConfig.id == config_id).first()
    if not config:
        raise NotFoundException("Assessment config not found")
    db.delete(config)
    db.commit()
    log_action(db, current_user, "Deleted assessment config", "assessment_config", str(config_id))
    return {"message": "Assessment config deleted"}


@router.post("/assessment-configs/batch")
@limiter.limit("30/minute")
def batch_create_assessment_configs(
    request: Request,
    data: BatchAssessmentConfigCreate,
    current_user: User = Depends(require_permission(CURRICULUM_MANAGE)),
    db: Session = Depends(get_db),
):
    created = []
    for cs_id in data.class_subject_ids:
        cs = db.query(ClassSubject).filter(ClassSubject.id == cs_id).first()
        if not cs:
            continue
        existing = {c.name: c for c in db.query(AssessmentConfig).filter(AssessmentConfig.class_subject_id == cs_id).all()}
        supplied_names = set()
        for i, cfg in enumerate(data.configs):
            supplied_names.add(cfg.name)
            if cfg.name in existing:
                old = existing[cfg.name]
                old.max_score = cfg.max_score
                old.sort_order = cfg.sort_order or i
                old.is_exam = cfg.is_exam
                created.append(old)
            else:
                config = AssessmentConfig(
                    class_subject_id=cs_id,
                    name=cfg.name,
                    max_score=cfg.max_score,
                    sort_order=cfg.sort_order or i,
                    is_exam=cfg.is_exam,
                )
                db.add(config)
                created.append(config)
        # Remove configs that are no longer in the supplied list
        for name, old in existing.items():
            if name not in supplied_names:
                db.delete(old)

    for cs_id in data.class_subject_ids:
        total = db.query(func.coalesce(func.sum(AssessmentConfig.max_score), 0)).filter(
            AssessmentConfig.class_subject_id == cs_id
        ).scalar()
        db.query(ClassSubject).filter(ClassSubject.id == cs_id).update(
            {"max_score": total}
        )
    db.commit()
    log_action(db, current_user, "Batch saved assessment configs", "assessment_config")
    return {"message": f"Assessment configs applied to {len(data.class_subject_ids)} subject(s)"}


@router.get("/assessment-configs/has-scores")
@limiter.limit("120/minute")
def check_assessment_configs_have_scores(
    request: Request,
    class_subject_ids: str = Query(..., description="Comma-separated list of class_subject UUIDs"),
    current_user: User = Depends(require_permission(CURRICULUM_VIEW)),
    db: Session = Depends(get_db),
):
    ids = [UUID(id_str.strip()) for id_str in class_subject_ids.split(",") if id_str.strip()]
    rows = db.query(
        AssessmentScore.class_subject_id,
        func.count(AssessmentScore.id)
    ).filter(
        AssessmentScore.class_subject_id.in_(ids)
    ).group_by(AssessmentScore.class_subject_id).all()
    has_scores = {str(row[0]): row[1] > 0 for row in rows}
    return {str(cs_id): has_scores.get(str(cs_id), False) for cs_id in ids}


# ─── Assessment Scores ─────────────────────────────────────────────────────


@router.post("/assessment-scores/batch")
@limiter.limit("30/minute")
def submit_assessment_scores_batch(
    request: Request,
    data: AssessmentScoreBatchCreate,
    current_user: User = Depends(require_permission(GRADES_SUBMIT)),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    recorder = get_staff_for_user(current_user, db)
    if not recorder:
        raise BadRequestException("Staff profile required to record grades")
    recorded_by_id = recorder.id
    for s in data.scores:
        existing = db.query(AssessmentScore).filter(
            AssessmentScore.student_id == s.student_id,
            AssessmentScore.class_subject_id == s.class_subject_id,
            AssessmentScore.term_id == data.term_id,
            AssessmentScore.assessment_config_id == s.assessment_config_id,
        ).first()
        if existing:
            existing.score = s.score
            existing.recorded_by = recorded_by_id
            existing.recorded_at = now
        else:
            record = AssessmentScore(
                student_id=s.student_id,
                class_subject_id=s.class_subject_id,
                term_id=data.term_id,
                assessment_config_id=s.assessment_config_id,
                score=s.score,
                recorded_by=recorded_by_id,
                recorded_at=now,
            )
            db.add(record)
    db.commit()
    log_action(db, current_user, "Submitted assessment scores", "assessment_score")
    return {"message": f"{len(data.scores)} assessment scores saved"}


@router.get("/assessment-scores", response_model=list[AssessmentScoreResponse])
@limiter.limit("120/minute")
def list_assessment_scores(
    request: Request,
    class_id: UUID | None = Query(None),
    class_subject_id: UUID | None = Query(None),
    term_id: UUID | None = Query(None),
    student_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission(GRADES_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(AssessmentScore)
    if class_id:
        query = query.join(Student, AssessmentScore.student_id == Student.id)
        query = query.filter(Student.current_class_id == class_id)
    if class_subject_id:
        query = query.filter(AssessmentScore.class_subject_id == class_subject_id)
    if term_id:
        query = query.filter(AssessmentScore.term_id == term_id)
    if student_id:
        query = query.filter(AssessmentScore.student_id == student_id)
    return query.order_by(AssessmentScore.recorded_at.desc()).limit(500).all()


# ─── Grades / Academic Records ────────────────────────────────────────────

@router.get("/grades", response_model=list[AcademicRecordResponse])
@limiter.limit("120/minute")
def list_grades(
    request: Request,
    class_id: UUID | None = Query(None),
    subject_id: UUID | None = Query(None),
    term_id: UUID | None = Query(None),
    student_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission(GRADES_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(AcademicRecord)

    tcid = get_user_teacher_id(current_user, db)
    if tcid:
        query = query.join(Student, AcademicRecord.student_id == Student.id)
        query = query.filter(Student.current_class_id == tcid)
        if class_id:
            query = query.filter(Student.current_class_id == class_id)
    elif current_user.role == "teacher":
        staff = get_staff_for_user(current_user, db)
        if staff:
            query = query.join(Student, AcademicRecord.student_id == Student.id)
            query = query.join(SchoolClass, Student.current_class_id == SchoolClass.id)
            query = query.filter(SchoolClass.teacher_id == staff.id)
    elif class_id:
        query = query.join(Student, AcademicRecord.student_id == Student.id)
        query = query.filter(Student.current_class_id == class_id)

    if subject_id:
        query = query.join(ClassSubject, AcademicRecord.class_subject_id == ClassSubject.id)
        query = query.filter(ClassSubject.subject_id == subject_id)
    if term_id:
        query = query.filter(AcademicRecord.term_id == term_id)
    if student_id:
        query = query.filter(AcademicRecord.student_id == student_id)

    return query.order_by(AcademicRecord.recorded_at.desc()).limit(500).all()


@router.post("/grades/batch")
@limiter.limit("30/minute")
def submit_grades_batch(
    request: Request,
    data: GradeBatchCreate,
    current_user: User = Depends(require_permission(GRADES_SUBMIT)),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    recorder = get_staff_for_user(current_user, db)
    if not recorder:
        raise BadRequestException("Staff profile required to record grades")
    recorded_by_id = recorder.id
    for g in data.grades:
        existing = db.query(AcademicRecord).filter(
            AcademicRecord.student_id == g.student_id,
            AcademicRecord.class_subject_id == g.class_subject_id,
            AcademicRecord.term_id == data.term_id,
        ).first()
        if existing:
            existing.score = g.score
            existing.max_score = g.max_score
            existing.recorded_by = recorded_by_id
            existing.recorded_at = now
        else:
            record = AcademicRecord(
                student_id=g.student_id,
                class_subject_id=g.class_subject_id,
                term_id=data.term_id,
                score=g.score,
                max_score=g.max_score,
                recorded_by=recorded_by_id,
                recorded_at=now,
            )
            db.add(record)
    db.commit()
    log_action(db, current_user, "Submitted grades batch", "grade")
    return {"message": f"{len(data.grades)} grades saved"}


@router.post("/grades", response_model=AcademicRecordResponse, status_code=201)
@limiter.limit("30/minute")
def create_grade(
    request: Request,
    data: AcademicRecordCreate,
    current_user: User = Depends(require_permission(GRADES_SUBMIT)),
    db: Session = Depends(get_db),
):
    recorder = get_staff_for_user(current_user, db)
    if not recorder:
        raise BadRequestException("Staff profile required to record grades")
    recorded_by_id = recorder.id
    existing = db.query(AcademicRecord).filter(
        AcademicRecord.student_id == data.student_id,
        AcademicRecord.class_subject_id == data.class_subject_id,
        AcademicRecord.term_id == data.term_id,
    ).first()
    if existing:
        existing.score = data.score
        existing.max_score = data.max_score
        existing.recorded_by = recorded_by_id
        existing.recorded_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing
    record = AcademicRecord(
        student_id=data.student_id,
        class_subject_id=data.class_subject_id,
        term_id=data.term_id,
        score=data.score,
        max_score=data.max_score,
        recorded_by=recorded_by_id,
    )
    db.add(record)
    db.commit()
    log_action(db, current_user, "Saved grade", "grade")
    db.refresh(record)
    return record


# ─── Attendance ────────────────────────────────────────────────────────────

@router.get("/attendance", response_model=list[AttendanceResponse])
@limiter.limit("120/minute")
def list_attendance(
    request: Request,
    class_id: UUID | None = Query(None),
    date_param: date | None = Query(None, alias="date"),
    student_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission(ATTENDANCE_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Attendance)

    tcid = get_user_teacher_id(current_user, db)
    if tcid:
        query = query.filter(Attendance.class_id == tcid)
    elif current_user.role == "teacher":
        staff = get_staff_for_user(current_user, db)
        if staff:
            query = query.join(SchoolClass, Attendance.class_id == SchoolClass.id)
            query = query.filter(SchoolClass.teacher_id == staff.id)

    if class_id:
        query = query.filter(Attendance.class_id == class_id)
    if date_param:
        query = query.filter(Attendance.date == date_param)
    if student_id:
        query = query.filter(Attendance.student_id == student_id)

    return query.order_by(Attendance.date.desc(), Attendance.created_at).limit(500).all()


@router.post("/attendance/batch")
@limiter.limit("30/minute")
def submit_attendance_batch(
    request: Request,
    data: AttendanceBatchCreate,
    current_user: User = Depends(require_permission(ATTENDANCE_SUBMIT)),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    recorder = get_staff_for_user(current_user, db)
    if not recorder:
        raise BadRequestException("Staff profile required to record attendance")
    recorded_by_id = recorder.id
    for r in data.records:
        existing = db.query(Attendance).filter(
            Attendance.student_id == r.student_id,
            Attendance.class_id == data.class_id,
            Attendance.date == data.date,
        ).first()
        if existing:
            existing.status = r.status
            existing.recorded_by = recorded_by_id
            existing.recorded_at = now
        else:
            att = Attendance(
                student_id=r.student_id,
                class_id=data.class_id,
                date=data.date,
                status=r.status,
                recorded_by=recorded_by_id,
                recorded_at=now,
            )
            db.add(att)
    db.commit()
    log_action(db, current_user, "Submitted attendance batch", "attendance")
    return {"message": f"{len(data.records)} attendance records saved"}


@router.post("/attendance", response_model=AttendanceResponse, status_code=201)
@limiter.limit("30/minute")
def create_attendance(
    request: Request,
    data: AttendanceCreate,
    current_user: User = Depends(require_permission(ATTENDANCE_SUBMIT)),
    db: Session = Depends(get_db),
):
    recorder = get_staff_for_user(current_user, db)
    if not recorder:
        raise BadRequestException("Staff profile required to record attendance")
    recorded_by_id = recorder.id
    existing = db.query(Attendance).filter(
        Attendance.student_id == data.student_id,
        Attendance.class_id == data.class_id,
        Attendance.date == data.date,
    ).first()
    if existing:
        existing.status = data.status
        existing.recorded_by = recorded_by_id
        existing.recorded_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing
    att = Attendance(
        student_id=data.student_id,
        class_id=data.class_id,
        date=data.date,
        status=data.status,
        recorded_by=recorded_by_id,
    )
    db.add(att)
    db.commit()
    log_action(db, current_user, "Saved attendance", "attendance")
    db.refresh(att)
    return att


# ─── Staff / Teachers ──────────────────────────────────────────────────────

@router.get("/teachers")
@limiter.limit("120/minute")
def list_teachers_for_assignment(
    request: Request,
    current_user: User = Depends(require_permission(STAFF_VIEW)),
    db: Session = Depends(get_db),
):
    staff = db.query(Staff).filter(
        Staff.role.in_(["teacher", "hr", "proprietor"]),
        Staff.is_active == True,
    ).order_by(Staff.first_name, Staff.last_name).all()
    return [
        {
            "id": str(s.id),
            "full_name": f"{s.first_name} {s.last_name}",
            "email": s.email,
            "role": s.role,
            "permissions": s.user_rel.permissions if s.user_rel else None,
        }
        for s in staff
    ]


@router.post("/staff-from-teachers", status_code=201)
@limiter.limit("30/minute")
def create_staff_from_teachers_endpoint(
    request: Request,
    data: dict,
    current_user: User = Depends(require_permission(STAFF_CREATE)),
    db: Session = Depends(get_db),
):
    from app.schemas.staff import StaffCreate
    from app.api.school.staff_routes import create_staff
    sc = StaffCreate(
        first_name=data.get("full_name", "").split(" ")[0] if data.get("full_name") else "",
        last_name=data.get("full_name", "").split(" ")[-1] if data.get("full_name") else "",
        email=data.get("email"),
        role=data.get("role", "teacher"),
        permissions=data.get("permissions"),
        create_login=True,
        login_email=data.get("email"),
        login_password=data.get("password") or secrets.token_urlsafe(12),
    )
    result = create_staff(sc, current_user, db)
    log_action(db, current_user, "Created staff", "staff")
    return result


# ─── Syllabus ─────────────────────────────────────────────────────────────


def build_tree_from_list(topics: list[SyllabusTopic]) -> list[SyllabusTopicResponse]:
    topic_map = {t.id: t for t in topics}
    children_map = {}
    for t in topics:
        if t.parent_id:
            children_map.setdefault(str(t.parent_id), []).append(t)

    def make_response(t: SyllabusTopic) -> SyllabusTopicResponse:
        return SyllabusTopicResponse(
            id=t.id,
            class_subject_id=t.class_subject_id,
            subject_id=t.subject_id,
            term_id=t.term_id,
            parent_id=t.parent_id,
            title=t.title,
            content=t.content,
            week_number=t.week_number,
            sort_order=t.sort_order,
            is_completed=t.is_completed,
            created_at=t.created_at,
            updated_at=t.updated_at,
            children=[make_response(c) for c in children_map.get(str(t.id), [])],
        )

    roots = [t for t in topics if t.parent_id is None]
    return [make_response(t) for t in roots]


@router.get("/syllabus", response_model=list[SyllabusTopicResponse])
@limiter.limit("120/minute")
def list_syllabus(
    request: Request,
    class_subject_id: UUID | None = Query(None),
    subject_id: UUID | None = Query(None),
    term_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission(SYLLABUS_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(SyllabusTopic).filter(SyllabusTopic.parent_id == None)
    if class_subject_id:
        query = query.filter(SyllabusTopic.class_subject_id == class_subject_id)
    if subject_id:
        query = query.filter(SyllabusTopic.subject_id == subject_id)
    if term_id:
        query = query.filter(SyllabusTopic.term_id == term_id)
    tcid = get_user_teacher_id(current_user, db)
    if tcid:
        query = query.join(ClassSubject, SyllabusTopic.class_subject_id == ClassSubject.id)
        query = query.filter(ClassSubject.class_id == tcid)
    elif current_user.role == "teacher":
        staff = get_staff_for_user(current_user, db)
        if staff:
            query = query.join(ClassSubject, SyllabusTopic.class_subject_id == ClassSubject.id)
            query = query.join(SchoolClass, ClassSubject.class_id == SchoolClass.id)
            query = query.filter(SchoolClass.teacher_id == staff.id)
    topics = query.order_by(SyllabusTopic.sort_order, SyllabusTopic.week_number).all()

    if topics:
        class_subject_ids = list(set(t.class_subject_id for t in topics if t.class_subject_id))
        all_topics = db.query(SyllabusTopic).filter(
            SyllabusTopic.class_subject_id.in_(class_subject_ids)
        ).order_by(SyllabusTopic.sort_order, SyllabusTopic.week_number).all()
    else:
        all_topics = []

    children_map: dict[str, list[SyllabusTopic]] = {}
    for t in all_topics:
        if t.parent_id:
            children_map.setdefault(str(t.parent_id), []).append(t)

    def make_response(t: SyllabusTopic) -> SyllabusTopicResponse:
        return SyllabusTopicResponse(
            id=t.id,
            class_subject_id=t.class_subject_id,
            subject_id=t.subject_id,
            term_id=t.term_id,
            parent_id=t.parent_id,
            title=t.title,
            content=t.content,
            week_number=t.week_number,
            sort_order=t.sort_order,
            is_completed=t.is_completed,
            created_at=t.created_at,
            updated_at=t.updated_at,
            children=[make_response(c) for c in children_map.get(str(t.id), [])],
        )

    roots = [t for t in all_topics if t.parent_id is None]
    return [make_response(r) for r in roots]


@router.get("/syllabus/{topic_id}", response_model=SyllabusTopicResponse)
@limiter.limit("120/minute")
def get_syllabus_topic(
    request: Request,
    topic_id: UUID,
    current_user: User = Depends(require_permission(SYLLABUS_VIEW)),
    db: Session = Depends(get_db),
):
    topic = db.query(SyllabusTopic).filter(SyllabusTopic.id == topic_id).first()
    if not topic:
        raise NotFoundException("Syllabus topic not found")

    all_topics = db.query(SyllabusTopic).filter(
        SyllabusTopic.class_subject_id == topic.class_subject_id
    ).order_by(SyllabusTopic.sort_order, SyllabusTopic.week_number).all() if topic.class_subject_id else [topic]

    children_map: dict[str, list[SyllabusTopic]] = {}
    for t in all_topics:
        if t.parent_id:
            children_map.setdefault(str(t.parent_id), []).append(t)

    def make_response(t: SyllabusTopic) -> SyllabusTopicResponse:
        return SyllabusTopicResponse(
            id=t.id,
            class_subject_id=t.class_subject_id,
            subject_id=t.subject_id,
            term_id=t.term_id,
            parent_id=t.parent_id,
            title=t.title,
            content=t.content,
            week_number=t.week_number,
            sort_order=t.sort_order,
            is_completed=t.is_completed,
            created_at=t.created_at,
            updated_at=t.updated_at,
            children=[make_response(c) for c in children_map.get(str(t.id), [])],
        )

    return make_response(topic)


@router.post("/syllabus", response_model=SyllabusTopicResponse, status_code=201)
@limiter.limit("30/minute")
def create_syllabus_topic(
    request: Request,
    data: SyllabusTopicCreate,
    current_user: User = Depends(require_permission(SYLLABUS_MANAGE)),
    db: Session = Depends(get_db),
):
    vals = data.model_dump()
    if not vals.get("term_id"):
        cs = None
        if vals.get("class_subject_id"):
            cs = db.query(ClassSubject).options(joinedload(ClassSubject.class_rel)).filter(ClassSubject.id == vals["class_subject_id"]).first()
        if not cs and vals.get("subject_id"):
            cs = db.query(ClassSubject).options(joinedload(ClassSubject.class_rel)).filter(ClassSubject.subject_id == vals["subject_id"]).first()
        if cs and cs.class_rel and cs.class_rel.academic_term_id:
            vals["term_id"] = cs.class_rel.academic_term_id
        if not vals.get("term_id"):
            raise BadRequestException("No term specified")
    # Auto-assign sort_order to end of sibling group
    parent_id = vals.get("parent_id")
    query = db.query(func.max(SyllabusTopic.sort_order))
    if parent_id:
        query = query.filter(SyllabusTopic.parent_id == parent_id, SyllabusTopic.class_subject_id == vals.get("class_subject_id"), SyllabusTopic.subject_id == vals.get("subject_id"))
    else:
        query = query.filter(SyllabusTopic.parent_id == None, SyllabusTopic.class_subject_id == vals.get("class_subject_id"), SyllabusTopic.subject_id == vals.get("subject_id"))
    max_order = query.scalar()
    vals["sort_order"] = (max_order or 0) + 1
    topic = SyllabusTopic(**vals)
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return SyllabusTopicResponse(
        id=topic.id,
        class_subject_id=topic.class_subject_id,
        subject_id=topic.subject_id,
        term_id=topic.term_id,
        parent_id=topic.parent_id,
        title=topic.title,
        content=topic.content,
        week_number=topic.week_number,
        sort_order=topic.sort_order,
        is_completed=topic.is_completed,
        created_at=topic.created_at,
        updated_at=topic.updated_at,
        children=[],
    )


@router.patch("/syllabus/{topic_id}", response_model=SyllabusTopicResponse)
@limiter.limit("30/minute")
def update_syllabus_topic(
    request: Request,
    topic_id: UUID,
    data: SyllabusTopicUpdate,
    current_user: User = Depends(require_permission(SYLLABUS_MANAGE)),
    db: Session = Depends(get_db),
):
    topic = db.query(SyllabusTopic).filter(SyllabusTopic.id == topic_id).first()
    if not topic:
        raise NotFoundException("Syllabus topic not found")
    for key, val in data.model_dump(exclude_none=True).items():
        setattr(topic, key, val)
    db.commit()
    db.refresh(topic)

    if topic.class_subject_id:
        all_topics = db.query(SyllabusTopic).filter(
            SyllabusTopic.class_subject_id == topic.class_subject_id
        ).order_by(SyllabusTopic.sort_order, SyllabusTopic.week_number).all()
    else:
        all_topics = [topic]

    result = build_tree_from_list(all_topics)
    for r in result:
        if r.id == topic.id:
            return r
    return result[0] if result else build_tree_from_list([topic])[0]


@router.delete("/syllabus/{topic_id}")
@limiter.limit("30/minute")
def delete_syllabus_topic(
    request: Request,
    topic_id: UUID,
    current_user: User = Depends(require_permission(SYLLABUS_MANAGE)),
    db: Session = Depends(get_db),
):
    topic = db.query(SyllabusTopic).filter(SyllabusTopic.id == topic_id).first()
    if not topic:
        raise NotFoundException("Syllabus topic not found")
    deleted_order = topic.sort_order
    del_parent_id = topic.parent_id
    del_class_subject_id = topic.class_subject_id
    del_subject_id = topic.subject_id
    db.delete(topic)
    db.flush()
    # Reindex remaining siblings
    siblings = db.query(SyllabusTopic).filter(
        SyllabusTopic.parent_id == del_parent_id,
        SyllabusTopic.class_subject_id == del_class_subject_id,
        SyllabusTopic.subject_id == del_subject_id,
        SyllabusTopic.sort_order > deleted_order,
    ).order_by(SyllabusTopic.sort_order).all()
    for sib in siblings:
        sib.sort_order -= 1
    db.commit()
    return {"message": "Syllabus topic deleted"}


@router.patch("/syllabus/{topic_id}/move", response_model=SyllabusTopicResponse)
@limiter.limit("30/minute")
def move_syllabus_topic(
    request: Request,
    topic_id: UUID,
    data: SyllabusTopicMove,
    current_user: User = Depends(require_permission(SYLLABUS_MANAGE)),
    db: Session = Depends(get_db),
):
    topic = db.query(SyllabusTopic).filter(SyllabusTopic.id == topic_id).first()
    if not topic:
        raise NotFoundException("Syllabus topic not found")
    parent_id = topic.parent_id
    class_subject_id = topic.class_subject_id
    subject_id = topic.subject_id
    current_order = topic.sort_order
    # Base sibling filters (no direction constraint)
    base_filters = [
        SyllabusTopic.parent_id == parent_id,
        SyllabusTopic.class_subject_id == class_subject_id,
        SyllabusTopic.subject_id == subject_id,
    ]
    # Find the adjacent sibling
    if data.direction == "up":
        neighbor = db.query(SyllabusTopic).filter(
            *base_filters, SyllabusTopic.sort_order < current_order
        ).order_by(SyllabusTopic.sort_order.desc()).first()
    else:
        neighbor = db.query(SyllabusTopic).filter(
            *base_filters, SyllabusTopic.sort_order > current_order
        ).order_by(SyllabusTopic.sort_order.asc()).first()
    if not neighbor:
        total_siblings = db.query(func.count(SyllabusTopic.id)).filter(*base_filters).scalar()
        if total_siblings <= 1:
            raise BadRequestException(f"Cannot move {data.direction} — already at the edge")
        siblings = db.query(SyllabusTopic).filter(*base_filters).order_by(SyllabusTopic.created_at).all()
        for i, sib in enumerate(siblings):
            sib.sort_order = i + 1
        db.commit()
        db.refresh(topic)
        current_order = topic.sort_order
        if data.direction == "up":
            neighbor = db.query(SyllabusTopic).filter(
                *base_filters, SyllabusTopic.sort_order < current_order
            ).order_by(SyllabusTopic.sort_order.desc()).first()
        else:
            neighbor = db.query(SyllabusTopic).filter(
                *base_filters, SyllabusTopic.sort_order > current_order
            ).order_by(SyllabusTopic.sort_order.asc()).first()
        if not neighbor:
            raise BadRequestException(f"Cannot move {data.direction} — already at the edge")
    topic.sort_order, neighbor.sort_order = neighbor.sort_order, topic.sort_order
    db.commit()
    db.refresh(topic)

    if topic.class_subject_id:
        all_topics = db.query(SyllabusTopic).filter(
            SyllabusTopic.class_subject_id == topic.class_subject_id
        ).order_by(SyllabusTopic.sort_order, SyllabusTopic.week_number).all()
    else:
        all_topics = [topic]

    result = build_tree_from_list(all_topics)
    for r in result:
        if r.id == topic.id:
            return r
    return result[0] if result else build_tree_from_list([topic])[0]


@router.post("/syllabus/reorder", status_code=200)
@limiter.limit("30/minute")
def reorder_syllabus_topics(
    request: Request,
    data: SyllabusTopicReorder,
    current_user: User = Depends(require_permission(SYLLABUS_MANAGE)),
    db: Session = Depends(get_db),
):
    for entry in data.topics:
        topic = db.query(SyllabusTopic).filter(SyllabusTopic.id == entry.id).first()
        if not topic:
            raise NotFoundException(f"Syllabus topic {entry.id} not found")
        topic.sort_order = entry.sort_order
    db.commit()
    return {"message": "Topics reordered"}


# ─── Syllabus Document ──────────────────────────────────────────────────────


@router.get("/syllabus/{class_subject_id}/document")
@limiter.limit("120/minute")
def get_syllabus_document(
    request: Request,
    class_subject_id: UUID,
    current_user: User = Depends(require_permission(SYLLABUS_VIEW)),
    db: Session = Depends(get_db),
):
    doc = db.query(SyllabusDocument).filter(
        SyllabusDocument.class_subject_id == class_subject_id
    ).first()
    if not doc:
        raise NotFoundException(detail="No syllabus document found for this class-subject")
    return {
        "id": str(doc.id),
        "class_subject_id": str(doc.class_subject_id),
        "file_url": doc.file_url,
        "original_filename": doc.original_filename,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
    }


@router.post("/syllabus/{class_subject_id}/document", status_code=201)
@limiter.limit("30/minute")
def upload_syllabus_document(
    request: Request,
    class_subject_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission(SYLLABUS_MANAGE)),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise BadRequestException(detail="Only PDF files are accepted")

    MAX_SYLLABUS_SIZE = 20 * 1024 * 1024
    content = file.file.read(MAX_SYLLABUS_SIZE + 1)
    if len(content) > MAX_SYLLABUS_SIZE:
        raise BadRequestException(detail="File too large (max 20MB)")
    if not validate_magic_bytes(content, ["application/pdf"]):
        raise BadRequestException(detail="Invalid file type - magic bytes validation failed")
    upload_svc = UploadService()
    safe_name = f"destined-images/syllabus/{uuid4()}.pdf"
    file_url, _ = upload_svc.upload(content, safe_name, "application/pdf")

    existing = db.query(SyllabusDocument).filter(
        SyllabusDocument.class_subject_id == class_subject_id
    ).first()
    if existing:
        db.delete(existing)
        db.flush()

    doc = SyllabusDocument(
        class_subject_id=class_subject_id,
        file_url=file_url,
        original_filename=file.filename,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "id": str(doc.id),
        "class_subject_id": str(doc.class_subject_id),
        "file_url": doc.file_url,
        "original_filename": doc.original_filename,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
    }


@router.delete("/syllabus/{class_subject_id}/document")
@limiter.limit("30/minute")
def delete_syllabus_document(
    request: Request,
    class_subject_id: UUID,
    current_user: User = Depends(require_permission(SYLLABUS_MANAGE)),
    db: Session = Depends(get_db),
):
    doc = db.query(SyllabusDocument).filter(
        SyllabusDocument.class_subject_id == class_subject_id
    ).first()
    if not doc:
        raise NotFoundException(detail="No syllabus document found for this class-subject")
    db.delete(doc)
    db.commit()
    return {"message": "Syllabus document deleted"}


@router.get("/syllabus/{class_subject_id}/document/file")
@limiter.limit("120/minute")
def serve_syllabus_document_file(
    request: Request,
    class_subject_id: UUID,
    current_user: User = Depends(require_permission(SYLLABUS_VIEW)),
    db: Session = Depends(get_db),
):
    doc = db.query(SyllabusDocument).filter(
        SyllabusDocument.class_subject_id == class_subject_id
    ).first()
    if not doc:
        raise NotFoundException(detail="No syllabus document found")
    headers = {"Content-Disposition": f'inline; filename="{doc.original_filename}"'}
    ALLOWED_DOMAINS = ["pub-13c02496b371428bbca75e924991d406.r2.dev", "localhost", "127.0.0.1"]
    parsed = urlparse(doc.file_url)
    netloc = parsed.netloc.split(":")[0].lower()
    if parsed.netloc and netloc not in ALLOWED_DOMAINS:
        raise NotFoundException(detail="Syllabus document not available")
    if doc.file_url.startswith("http"):
        try:
            resp = httpx.get(doc.file_url, timeout=10.0, follow_redirects=False)
            resp.raise_for_status()
            return StreamingResponse(
                iter([resp.content]),
                media_type="application/pdf",
                headers=headers,
            )
        except Exception:
            raise NotFoundException(detail="Syllabus document not available")
    local_path = os.path.join(
        UPLOAD_DIR, doc.file_url.replace("/uploads/", "")
    )
    return FileResponse(local_path, media_type="application/pdf", filename=doc.original_filename)


# ─── Time Periods ───────────────────────────────────────────────────────────

@router.get("/time-periods", response_model=list[TimePeriodResponse])
@limiter.limit("120/minute")
def list_time_periods(
    request: Request,
    current_user: User = Depends(require_permission(TIMETABLE_VIEW)),
    db: Session = Depends(get_db),
):
    periods = db.query(TimePeriod).order_by(TimePeriod.sort_order).limit(500).all()
    return [
        TimePeriodResponse(
            id=p.id, name=p.name,
            start_time=p.start_time.strftime("%H:%M") if hasattr(p.start_time, "strftime") else str(p.start_time),
            end_time=p.end_time.strftime("%H:%M") if hasattr(p.end_time, "strftime") else str(p.end_time),
            sort_order=p.sort_order,
        )
        for p in periods
    ]


@router.post("/time-periods", response_model=TimePeriodResponse, status_code=201)
@limiter.limit("30/minute")
def create_time_period(
    request: Request,
    data: TimePeriodCreate,
    current_user: User = Depends(require_permission(TIMETABLE_MANAGE)),
    db: Session = Depends(get_db),
):
    from datetime import time
    period = TimePeriod(
        name=data.name,
        start_time=time.fromisoformat(data.start_time),
        end_time=time.fromisoformat(data.end_time),
        sort_order=data.sort_order,
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return TimePeriodResponse(
        id=period.id, name=period.name,
        start_time=period.start_time.strftime("%H:%M"),
        end_time=period.end_time.strftime("%H:%M"),
        sort_order=period.sort_order,
    )


@router.patch("/time-periods/{period_id}", response_model=TimePeriodResponse)
@limiter.limit("30/minute")
def update_time_period(
    request: Request,
    period_id: UUID,
    data: TimePeriodUpdate,
    current_user: User = Depends(require_permission(TIMETABLE_MANAGE)),
    db: Session = Depends(get_db),
):
    from datetime import time
    period = db.query(TimePeriod).filter(TimePeriod.id == period_id).first()
    if not period:
        raise NotFoundException("Time period not found")
    if data.name is not None:
        period.name = data.name
    if data.start_time is not None:
        period.start_time = time.fromisoformat(data.start_time)
    if data.end_time is not None:
        period.end_time = time.fromisoformat(data.end_time)
    if data.sort_order is not None:
        period.sort_order = data.sort_order
    db.commit()
    db.refresh(period)
    return TimePeriodResponse(
        id=period.id, name=period.name,
        start_time=period.start_time.strftime("%H:%M"),
        end_time=period.end_time.strftime("%H:%M"),
        sort_order=period.sort_order,
    )


@router.delete("/time-periods/{period_id}")
@limiter.limit("30/minute")
def delete_time_period(
    request: Request,
    period_id: UUID,
    current_user: User = Depends(require_permission(TIMETABLE_MANAGE)),
    db: Session = Depends(get_db),
):
    period = db.query(TimePeriod).filter(TimePeriod.id == period_id).first()
    if not period:
        raise NotFoundException("Time period not found")
    db.delete(period)
    db.commit()
    return {"message": "Time period deleted"}


# ─── Timetable ─────────────────────────────────────────────────────────────

@router.get("/timetable", response_model=list[TimetableEntryResponse])
@limiter.limit("120/minute")
def list_timetable(
    request: Request,
    class_id: UUID | None = Query(None),
    day_of_week: int | None = Query(None),
    current_user: User = Depends(require_permission(TIMETABLE_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(TimeTableEntry).options(
        joinedload(TimeTableEntry.time_period),
        joinedload(TimeTableEntry.class_subject).joinedload(ClassSubject.subject_rel),
        joinedload(TimeTableEntry.class_subject).joinedload(ClassSubject.teacher_rel),
    )
    if class_id:
        query = query.filter(TimeTableEntry.class_id == class_id)
    if day_of_week is not None:
        query = query.filter(TimeTableEntry.day_of_week == day_of_week)
    tcid = get_user_teacher_id(current_user, db)
    if tcid:
        query = query.filter(TimeTableEntry.class_id == tcid)
    elif current_user.role == "teacher":
        staff = get_staff_for_user(current_user, db)
        if staff:
            query = query.join(SchoolClass, TimeTableEntry.class_id == SchoolClass.id)
            query = query.filter(SchoolClass.teacher_id == staff.id)
    entries = query.order_by(TimeTableEntry.day_of_week, TimeTableEntry.time_period_id).limit(500).all()
    return [
        TimetableEntryResponse(
            id=e.id,
            class_id=e.class_id,
            day_of_week=e.day_of_week,
            time_period_id=e.time_period_id,
            class_subject_id=e.class_subject_id,
            room=e.room,
            time_period_name=e.time_period.name if e.time_period else None,
            subject_name=e.class_subject.subject_rel.name if e.class_subject and e.class_subject.subject_rel else None,
            subject_code=e.class_subject.subject_rel.code if e.class_subject and e.class_subject.subject_rel else None,
            teacher_name=f"{e.class_subject.teacher_rel.first_name} {e.class_subject.teacher_rel.last_name}" if e.class_subject and e.class_subject.teacher_rel else None,
        )
        for e in entries
    ]


@router.post("/timetable", response_model=TimetableEntryResponse, status_code=201)
@limiter.limit("30/minute")
def create_timetable_entry(
    request: Request,
    data: TimetableEntryCreate,
    current_user: User = Depends(require_permission(TIMETABLE_MANAGE)),
    db: Session = Depends(get_db),
):
    entry = TimeTableEntry(**data.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    entry = db.query(TimeTableEntry).options(
        joinedload(TimeTableEntry.time_period),
        joinedload(TimeTableEntry.class_subject).joinedload(ClassSubject.subject_rel),
        joinedload(TimeTableEntry.class_subject).joinedload(ClassSubject.teacher_rel),
    ).filter(TimeTableEntry.id == entry.id).first()
    return TimetableEntryResponse(
        id=entry.id,
        class_id=entry.class_id,
        day_of_week=entry.day_of_week,
        time_period_id=entry.time_period_id,
        class_subject_id=entry.class_subject_id,
        room=entry.room,
        time_period_name=entry.time_period.name if entry.time_period else None,
        subject_name=entry.class_subject.subject_rel.name if entry.class_subject and entry.class_subject.subject_rel else None,
        subject_code=entry.class_subject.subject_rel.code if entry.class_subject and entry.class_subject.subject_rel else None,
        teacher_name=f"{entry.class_subject.teacher_rel.first_name} {entry.class_subject.teacher_rel.last_name}" if entry.class_subject and entry.class_subject.teacher_rel else None,
    )


@router.patch("/timetable/{entry_id}", response_model=TimetableEntryResponse)
@limiter.limit("30/minute")
def update_timetable_entry(
    request: Request,
    entry_id: UUID,
    data: TimetableEntryUpdate,
    current_user: User = Depends(require_permission(TIMETABLE_MANAGE)),
    db: Session = Depends(get_db),
):
    entry = db.query(TimeTableEntry).filter(TimeTableEntry.id == entry_id).first()
    if not entry:
        raise NotFoundException("Timetable entry not found")
    for key, val in data.model_dump(exclude_none=True).items():
        setattr(entry, key, val)
    db.commit()
    db.refresh(entry)
    entry = db.query(TimeTableEntry).options(
        joinedload(TimeTableEntry.time_period),
        joinedload(TimeTableEntry.class_subject).joinedload(ClassSubject.subject_rel),
        joinedload(TimeTableEntry.class_subject).joinedload(ClassSubject.teacher_rel),
    ).filter(TimeTableEntry.id == entry.id).first()
    return TimetableEntryResponse(
        id=entry.id,
        class_id=entry.class_id,
        day_of_week=entry.day_of_week,
        time_period_id=entry.time_period_id,
        class_subject_id=entry.class_subject_id,
        room=entry.room,
        time_period_name=entry.time_period.name if entry.time_period else None,
        subject_name=entry.class_subject.subject_rel.name if entry.class_subject and entry.class_subject.subject_rel else None,
        subject_code=entry.class_subject.subject_rel.code if entry.class_subject and entry.class_subject.subject_rel else None,
        teacher_name=f"{entry.class_subject.teacher_rel.first_name} {entry.class_subject.teacher_rel.last_name}" if entry.class_subject and entry.class_subject.teacher_rel else None,
    )


@router.delete("/timetable/{entry_id}")
@limiter.limit("30/minute")
def delete_timetable_entry(
    request: Request,
    entry_id: UUID,
    current_user: User = Depends(require_permission(TIMETABLE_MANAGE)),
    db: Session = Depends(get_db),
):
    entry = db.query(TimeTableEntry).filter(TimeTableEntry.id == entry_id).first()
    if not entry:
        raise NotFoundException("Timetable entry not found")
    db.delete(entry)
    db.commit()
    return {"message": "Timetable entry deleted"}


# ─── Reports ──────────────────────────────────────────────────────────────

@router.get("/reports/attendance")
@limiter.limit("120/minute")
def attendance_report(
    request: Request,
    class_id: UUID | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    current_user: User = Depends(require_permission(REPORTS_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(
        Attendance.date,
        Attendance.status,
        func.count(Attendance.id).label("count"),
    )
    if class_id:
        query = query.filter(Attendance.class_id == class_id)
    if start_date:
        query = query.filter(Attendance.date >= start_date)
    if end_date:
        query = query.filter(Attendance.date <= end_date)
    query = query.group_by(Attendance.date, Attendance.status).order_by(Attendance.date)
    rows = query.all()
    return [
        {"date": str(r[0]), "status": r[1], "count": r[2]}
        for r in rows
    ]


@router.get("/reports/grades")
@limiter.limit("120/minute")
def grade_report(
    request: Request,
    class_id: UUID | None = Query(None),
    subject_id: UUID | None = Query(None),
    term_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission(REPORTS_VIEW)),
    db: Session = Depends(get_db),
):
    scales = db.query(GradingScale).filter(GradingScale.is_active == True).order_by(GradingScale.min_score.desc()).all()

    query = db.query(
        Student.first_name,
        Student.last_name,
        Subject.name.label("subject_name"),
        AcademicRecord.class_subject_id,
        AcademicRecord.score,
        AcademicRecord.max_score,
        AcademicRecord.recorded_at,
    ).select_from(AcademicRecord)
    query = query.join(Student, AcademicRecord.student_id == Student.id)
    query = query.join(ClassSubject, AcademicRecord.class_subject_id == ClassSubject.id)
    query = query.join(Subject, ClassSubject.subject_id == Subject.id)

    if class_id:
        query = query.filter(Student.current_class_id == class_id)
    if subject_id:
        query = query.filter(ClassSubject.subject_id == subject_id)
    if term_id:
        query = query.filter(AcademicRecord.term_id == term_id)

    rows = []
    for r in query.order_by(Student.last_name, Student.first_name, Subject.name).all():
        grade, remark = _compute_grade(float(r[4] or 0), scales)
        rows.append({
            "student_name": f"{r[0]} {r[1]}",
            "subject": r[2],
            "score": r[4],
            "max_score": r[5],
            "grade": grade,
            "remark": remark,
            "recorded_at": str(r[6]),
        })
    return rows


# ─── Grading Scale ──────────────────────────────────────────────────────────

@router.get("/grading-scales", response_model=list[GradingScaleResponse])
@limiter.limit("120/minute")
def list_grading_scales(
    request: Request,
    current_user: User = Depends(require_permission(REPORTS_VIEW)),
    db: Session = Depends(get_db),
):
    return db.query(GradingScale).order_by(GradingScale.min_score.desc()).limit(500).all()


@router.post("/grading-scales", response_model=GradingScaleResponse, status_code=201)
@limiter.limit("30/minute")
def create_grading_scale(
    request: Request,
    data: GradingScaleCreate,
    current_user: User = Depends(require_permission(GRADING_MANAGE)),
    db: Session = Depends(get_db),
):
    existing = db.query(GradingScale).filter(
        GradingScale.grade == data.grade
    ).first()
    if existing:
        raise ConflictException("Grade already exists")
    scale = GradingScale(**data.model_dump())
    db.add(scale)
    db.commit()
    db.refresh(scale)
    log_action(db, current_user, "Created grading scale", "grading_scale", str(scale.id))
    return scale


@router.patch("/grading-scales/{scale_id}", response_model=GradingScaleResponse)
@limiter.limit("30/minute")
def update_grading_scale(
    request: Request,
    scale_id: UUID,
    data: GradingScaleUpdate,
    current_user: User = Depends(require_permission(GRADING_MANAGE)),
    db: Session = Depends(get_db),
):
    scale = db.query(GradingScale).filter(GradingScale.id == scale_id).first()
    if not scale:
        raise NotFoundException("Grading scale entry not found")
    for key, val in data.model_dump(exclude_none=True).items():
        setattr(scale, key, val)
    db.commit()
    log_action(db, current_user, "Updated grading scale", "grading_scale", str(scale_id))
    db.refresh(scale)
    return scale


@router.delete("/grading-scales/{scale_id}")
@limiter.limit("30/minute")
def delete_grading_scale(
    request: Request,
    scale_id: UUID,
    current_user: User = Depends(require_permission(GRADING_MANAGE)),
    db: Session = Depends(get_db),
):
    scale = db.query(GradingScale).filter(GradingScale.id == scale_id).first()
    if not scale:
        raise NotFoundException("Grading scale entry not found")
    db.delete(scale)
    db.commit()
    log_action(db, current_user, "Deleted grading scale", "grading_scale", str(scale_id))
    return {"message": "Grading scale entry deleted"}


# ─── Grading Info (for frontend) ───────────────────────────────────────────

@router.get("/grading-info", response_model=GradingInfoResponse)
@limiter.limit("120/minute")
def get_grading_info(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(REPORTS_VIEW)),
):
    scales = db.query(GradingScale).filter(GradingScale.is_active == True).order_by(GradingScale.min_score.desc()).all()
    return GradingInfoResponse(scales=[
        GradingScaleResponse(
            id=s.id, grade=s.grade, min_score=s.min_score,
            max_score=s.max_score, remark=s.remark, is_active=s.is_active,
            created_at=s.created_at, updated_at=s.updated_at,
        )
        for s in scales
    ])


# ─── Report Card ────────────────────────────────────────────────────────────

def _compute_grade(score: float, scales: list[GradingScale]) -> tuple[str, str]:
    for s in scales:
        if s.min_score <= score <= s.max_score:
            return s.grade, s.remark
    return "", ""


@router.get("/students/{student_id}/report-card", response_model=ReportCardResponse)
@limiter.limit("120/minute")
def get_report_card(
    request: Request,
    student_id: UUID,
    term_id: UUID | None = Query(None),
    current_user: User = Depends(require_permission(REPORTS_VIEW)),
    db: Session = Depends(get_db),
):
    student = db.query(Student).options(
        joinedload(Student.current_class_rel)
    ).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundException("Student not found")

    if not term_id:
        active_term = db.query(AcademicTerm).filter(AcademicTerm.is_active == True).first()
        if not active_term:
            raise BadRequestException("No active term set")
        term_id = active_term.id

    term = db.query(AcademicTerm).filter(AcademicTerm.id == term_id).first()
    if not term:
        raise NotFoundException("Term not found")

    scales = db.query(GradingScale).filter(GradingScale.is_active == True).order_by(GradingScale.min_score.desc()).all()

    class_subjects = db.query(ClassSubject).filter(
        ClassSubject.class_id == student.current_class_id
    ).options(
        joinedload(ClassSubject.subject_rel)
    ).all()

    # Load all AcademicRecords for this student/term in bulk
    all_ac_records = {
        (str(r.class_subject_id)): r
        for r in db.query(AcademicRecord).filter(
            AcademicRecord.student_id == student_id,
            AcademicRecord.term_id == term_id,
        ).all()
    }

    # Load all AssessmentScores for this student/term in bulk
    all_as_scores_list = db.query(AssessmentScore).filter(
        AssessmentScore.student_id == student_id,
        AssessmentScore.term_id == term_id,
    ).all()

    # Group assessment scores by class_subject_id
    as_by_cs: dict[str, list[AssessmentScore]] = {}
    for s in all_as_scores_list:
        csid = str(s.class_subject_id)
        as_by_cs.setdefault(csid, []).append(s)

    # Bulk-load all AssessmentConfigs for all class subjects (eliminates N+1)
    cs_ids = [cs.id for cs in class_subjects]
    all_configs = db.query(AssessmentConfig).filter(
        AssessmentConfig.class_subject_id.in_(cs_ids)
    ).order_by(AssessmentConfig.sort_order).all()
    configs_by_cs: dict[str, list[AssessmentConfig]] = {}
    for cfg in all_configs:
        csid = str(cfg.class_subject_id)
        configs_by_cs.setdefault(csid, []).append(cfg)

    subjects = []
    total_score = 0.0
    total_max_score = 0.0

    for cs in class_subjects:
        csid = str(cs.id)
        configs = configs_by_cs.get(csid, [])

        comment = ""

        if configs:
            scores = as_by_cs.get(csid, [])
            score_map = {str(s.assessment_config_id): s for s in scores}

            ca_scores: dict[str, float] = {}
            exam_score: float = 0.0
            ca_total = 0.0
            ca_max = 0.0
            exam_max = 0.0

            for cfg in configs:
                as_obj = score_map.get(str(cfg.id))
                val = as_obj.score if as_obj else 0.0
                if cfg.is_exam:
                    exam_score += val
                    exam_max += cfg.max_score
                    if as_obj and as_obj.teacher_comment:
                        comment = as_obj.teacher_comment
                else:
                    ca_scores[cfg.name] = val
                    ca_total += val
                    ca_max += cfg.max_score

            total = (ca_total + (exam_score or 0.0))
            total_max = ca_max + exam_max
            grade, remark = _compute_grade(total, scales)

            subjects.append(ReportCardSubject(
                subject_name=cs.subject_rel.name,
                subject_code=cs.subject_rel.code,
                score=total,
                max_score=total_max,
                grade=grade,
                remark=remark,
                ca_scores=ca_scores,
                exam_score=exam_score,
                ca_total=ca_total,
                exam_max=exam_max,
                ca_max=ca_max,
                is_assessment_based=True,
                comment=comment,
            ))
            total_score += total
            total_max_score += total_max
        else:
            # Fallback to legacy AcademicRecord
            ac = all_ac_records.get(csid)
            score = ac.score if ac else 0.0
            max_score = ac.max_score if ac else (cs.max_score or 100.0)
            grade, remark = _compute_grade(score, scales)
            comment = ac.teacher_comment if ac and ac.teacher_comment else ""

            subjects.append(ReportCardSubject(
                subject_name=cs.subject_rel.name,
                subject_code=cs.subject_rel.code,
                score=score,
                max_score=max_score,
                grade=grade,
                remark=remark,
                comment=comment,
            ))
            total_score += score
            total_max_score += max_score

    average = round(total_score / len(subjects), 2) if subjects else 0.0

    # Compute class position using bulk queries (AcademicRecord + AssessmentScore)
    class_student_ids = [
        r[0] for r in db.query(Student.id).filter(
            Student.current_class_id == student.current_class_id,
            Student.is_active == True,
        ).all()
    ]
    total_students = len(class_student_ids)

    class_subject_ids = [cs.id for cs in class_subjects]
    all_ac_records = db.query(AcademicRecord).filter(
        AcademicRecord.student_id.in_(class_student_ids),
        AcademicRecord.class_subject_id.in_(class_subject_ids),
        AcademicRecord.term_id == term_id,
    ).all()
    all_as_scores = db.query(AssessmentScore).filter(
        AssessmentScore.student_id.in_(class_student_ids),
        AssessmentScore.class_subject_id.in_(class_subject_ids),
        AssessmentScore.term_id == term_id,
    ).all()

    ac_totals: dict[str, float] = {}
    for r in all_ac_records:
        sid = str(r.student_id)
        ac_totals[sid] = ac_totals.get(sid, 0) + r.score

    as_totals: dict[str, float] = {}
    for s in all_as_scores:
        sid = str(s.student_id)
        as_totals[sid] = as_totals.get(sid, 0) + s.score

    position = 1
    num_subjects = len(class_subjects)
    if subjects and num_subjects > 0:
        student_avg = total_score / num_subjects
        for s_id in class_student_ids:
            sid = str(s_id)
            if sid == str(student_id):
                continue
            s_total = ac_totals.get(sid, 0) + as_totals.get(sid, 0)
            if (s_total / num_subjects) > student_avg:
                position += 1

    # Load ReportCardExtra
    extra = db.query(ReportCardExtra).filter(
        ReportCardExtra.student_id == student_id,
        ReportCardExtra.term_id == term_id,
    ).first()

    return ReportCardResponse(
        student_id=student.id,
        student_name=f"{student.first_name} {student.last_name}",
        admission_number=student.admission_number,
        class_name=student.current_class_rel.name if student.current_class_rel else "",
        term_name=term.name,
        term_year=term.year,
        subjects=subjects,
        total_score=total_score,
        total_max_score=total_max_score,
        average=average,
        position=position,
        total_students=total_students,
        # Extra fields
        times_school_opened=extra.times_school_opened if extra else None,
        times_present=extra.times_present if extra else None,
        times_absent=extra.times_absent if extra else None,
        punctuality=extra.punctuality if extra else None,
        neatness=extra.neatness if extra else None,
        leadership=extra.leadership if extra else None,
        demeanour=extra.demeanour if extra else None,
        literacy=extra.literacy if extra else None,
        sporting=extra.sporting if extra else None,
        cultural=extra.cultural if extra else None,
        proprietors_remarks=extra.proprietors_remarks if extra else None,
        teacher_remark=extra.teacher_remark if extra else None,
        tuition_fee=float(extra.tuition_fee) if extra and extra.tuition_fee else None,
        other_fees=float(extra.other_fees) if extra and extra.other_fees else None,
        total_fees=float(extra.total_fees) if extra and extra.total_fees else None,
        next_term_begin=extra.next_term_begin if extra else None,
        class_teacher_comment=extra.class_teacher_comment if extra else None,
        head_teacher_comment=extra.head_teacher_comment if extra else None,
    )


@router.put("/students/{student_id}/report-card-extra", response_model=dict)
@limiter.limit("30/minute")
def save_report_card_extra(
    request: Request,
    student_id: UUID,
    term_id: UUID = Query(...),
    data: ReportCardExtraSave = None,
    current_user: User = Depends(require_permission(REPORTS_VIEW)),
    db: Session = Depends(get_db),
):
    extra = db.query(ReportCardExtra).filter(
        ReportCardExtra.student_id == student_id,
        ReportCardExtra.term_id == term_id,
    ).first()

    if not extra:
        extra = ReportCardExtra(student_id=student_id, term_id=term_id)
        db.add(extra)

    if data is not None:
        for field in data.model_fields_set:
            setattr(extra, field, getattr(data, field))

    db.commit()
    log_action(db, current_user, "Saved report card extra", "report", str(student_id))
    return {"message": "Report card extra saved"}


@router.put("/students/{student_id}/report-card-comment", response_model=dict)
@limiter.limit("30/minute")
def save_subject_comment(
    request: Request,
    student_id: UUID,
    class_subject_id: UUID = Query(...),
    term_id: UUID = Query(...),
    comment: str = "",
    current_user: User = Depends(require_permission(GRADES_SUBMIT)),
    db: Session = Depends(get_db),
):
    ac = db.query(AcademicRecord).filter(
        AcademicRecord.student_id == student_id,
        AcademicRecord.class_subject_id == class_subject_id,
        AcademicRecord.term_id == term_id,
    ).first()
    if ac:
        ac.teacher_comment = comment
        db.commit()
        log_action(db, current_user, "Saved subject comment", "report", str(student_id))
        return {"message": "Comment saved"}

    as_scores = db.query(AssessmentScore).filter(
        AssessmentScore.student_id == student_id,
        AssessmentScore.class_subject_id == class_subject_id,
        AssessmentScore.term_id == term_id,
    ).first()
    if as_scores:
        as_scores.teacher_comment = comment
        db.commit()
        log_action(db, current_user, "Saved subject comment", "report", str(student_id))
        return {"message": "Comment saved"}

    raise NotFoundException("No record found for this student/subject/term")


# ─── Transcript ─────────────────────────────────────────────────────────────

@router.get("/students/{student_id}/transcript", response_model=TranscriptResponse)
@limiter.limit("120/minute")
def get_transcript(
    request: Request,
    student_id: UUID,
    current_user: User = Depends(require_permission(REPORTS_VIEW)),
    db: Session = Depends(get_db),
):
    student = db.query(Student).options(
        joinedload(Student.current_class_rel)
    ).filter(Student.id == student_id).first()
    if not student:
        raise NotFoundException("Student not found")

    scales = db.query(GradingScale).filter(GradingScale.is_active == True).order_by(GradingScale.min_score.desc()).all()
    terms = db.query(AcademicTerm).order_by(AcademicTerm.year, AcademicTerm.start_date).all()
    term_ids = [t.id for t in terms]

    # Bulk-load class subjects (once, same class for all terms)
    class_subjects = db.query(ClassSubject).filter(
        ClassSubject.class_id == student.current_class_id
    ).options(
        joinedload(ClassSubject.subject_rel)
    ).all()
    cs_ids = [cs.id for cs in class_subjects]

    # Bulk-load all AssessmentConfigs
    all_configs = db.query(AssessmentConfig).filter(
        AssessmentConfig.class_subject_id.in_(cs_ids)
    ).order_by(AssessmentConfig.sort_order).all()
    configs_by_cs: dict[str, list[AssessmentConfig]] = {}
    for cfg in all_configs:
        configs_by_cs.setdefault(str(cfg.class_subject_id), []).append(cfg)

    # Bulk-load all AssessmentScores for all terms
    all_scores = db.query(AssessmentScore).filter(
        AssessmentScore.student_id == student_id,
        AssessmentScore.class_subject_id.in_(cs_ids),
        AssessmentScore.term_id.in_(term_ids),
    ).all()
    scores_by_key: dict[tuple[str, str], list[AssessmentScore]] = {}
    for s in all_scores:
        key = (str(s.term_id), str(s.class_subject_id))
        scores_by_key.setdefault(key, []).append(s)

    # Bulk-load all AcademicRecords for all terms
    all_records = db.query(AcademicRecord).filter(
        AcademicRecord.student_id == student_id,
        AcademicRecord.class_subject_id.in_(cs_ids),
        AcademicRecord.term_id.in_(term_ids),
    ).all()
    records_by_key: dict[tuple[str, str], AcademicRecord] = {}
    for r in all_records:
        records_by_key[(str(r.term_id), str(r.class_subject_id))] = r

    term_results = []
    for term in terms:
        tid = str(term.id)
        subjects = []
        total_score = 0.0
        total_max_score = 0.0

        for cs in class_subjects:
            csid = str(cs.id)
            configs = configs_by_cs.get(csid, [])

            if configs:
                assessment_scores = scores_by_key.get((tid, csid), [])
                score_map = {str(s.assessment_config_id): s.score for s in assessment_scores}

                ca_scores: dict[str, float] = {}
                exam_score: float = 0.0
                ca_total = 0.0
                ca_max = 0.0
                exam_max = 0.0

                for cfg in configs:
                    val = score_map.get(str(cfg.id), 0.0)
                    if cfg.is_exam:
                        exam_score += val
                        exam_max += cfg.max_score
                    else:
                        ca_scores[cfg.name] = val
                        ca_total += val
                        ca_max += cfg.max_score

                total = ca_total + exam_score
                total_max = ca_max + exam_max
                grade, remark = _compute_grade(total, scales)

                subjects.append(ReportCardSubject(
                    subject_name=cs.subject_rel.name,
                    subject_code=cs.subject_rel.code,
                    score=total,
                    max_score=total_max,
                    grade=grade,
                    remark=remark,
                    ca_scores=ca_scores,
                    exam_score=exam_score,
                    ca_total=ca_total,
                    exam_max=exam_max,
                    ca_max=ca_max,
                    is_assessment_based=True,
                ))
                total_score += total
                total_max_score += total_max
            else:
                grade_record = records_by_key.get((tid, csid))
                score = grade_record.score if grade_record else 0.0
                max_score = grade_record.max_score if grade_record else (cs.max_score or 100.0)
                grade, remark = _compute_grade(score, scales)

                subjects.append(ReportCardSubject(
                    subject_name=cs.subject_rel.name,
                    subject_code=cs.subject_rel.code,
                    score=score,
                    max_score=max_score,
                    grade=grade,
                    remark=remark,
                ))
                total_score += score
                total_max_score += max_score

        average = round(total_score / len(subjects), 2) if subjects else 0.0

        term_results.append(TranscriptTerm(
            term_id=term.id,
            term_name=term.name,
            year=term.year,
            subjects=subjects,
            total_score=total_score,
            total_max_score=total_max_score,
            average=average,
        ))

    return TranscriptResponse(
        student_id=student.id,
        student_name=f"{student.first_name} {student.last_name}",
        admission_number=student.admission_number,
        terms=term_results,
    )


# ─── Outlist ────────────────────────────────────────────────────────────────

@router.get("/students/outlist", response_model=OutlistResponse)
@limiter.limit("120/minute")
def get_outlist(
    request: Request,
    status: str | None = Query(None, description="Comma-separated statuses: graduated,withdrawn,suspended"),
    current_user: User = Depends(require_permission(REPORTS_VIEW)),
    db: Session = Depends(get_db),
):
    query = db.query(Student).outerjoin(SchoolClass, Student.current_class_id == SchoolClass.id)

    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        query = query.filter(Student.status.in_(statuses))
    else:
        query = query.filter(Student.status.in_(["graduated", "withdrawn", "suspended"]))

    students = query.order_by(Student.last_name, Student.first_name).all()
    return OutlistResponse(students=[
        OutlistStudent(
            id=s.id,
            first_name=s.first_name,
            middle_name=s.middle_name,
            last_name=s.last_name,
            admission_number=s.admission_number,
            status=s.status,
            class_name=s.current_class_rel.name if s.current_class_rel else None,
            date_of_admission=s.date_of_admission,
            parent_name=s.parent_name,
            parent_phone=s.parent_phone,
            emergency_contact=s.emergency_contact,
        )
        for s in students
    ])
