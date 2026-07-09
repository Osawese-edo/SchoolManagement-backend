"""Test grading scales, report card, transcript, and outlist endpoints."""
import os, sys, uuid
from datetime import date, datetime, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient
from app.main import create_app
from app.db.session import engine, SessionLocal
from app.models.user import User
from app.models.academic_term import AcademicTerm
from app.models.school_class import SchoolClass
from app.models.subject import Subject
from app.models.class_subject import ClassSubject
from app.models.student import Student
from app.models.academic_record import AcademicRecord
from app.models.grading_scale import GradingScale
from app.models.staff import Staff
from app.core.security import hash_password
from app.db.session import Base

# Ensure all tables exist
Base.metadata.create_all(bind=engine)

def seed_data(db) -> dict:
    """Create test data and return references."""
    now = datetime.now(timezone.utc)

    staff = Staff(
        first_name="Test", last_name="Teacher",
        email="teacher@test.com", role="teacher", is_active=True,
    )
    db.add(staff)
    db.flush()

    term = AcademicTerm(name="First Term", year="2025/2026",
                        start_date=date(2025,9,1), end_date=date(2025,12,31),
                        is_active=False)
    db.add(term)
    db.flush()

    cls = SchoolClass(name="Grade 1", academic_term_id=term.id, is_active=True)
    db.add(cls)
    db.flush()

    subj = Subject(name="Mathematics", code="MTH101")
    db.add(subj)
    db.flush()

    cs = ClassSubject(class_id=cls.id, subject_id=subj.id, teacher_id=staff.id, max_score=100.0)
    db.add(cs)
    db.flush()

    uid = uuid.uuid4().hex[:8]
    student = Student(
        first_name="John", last_name="Doe", middle_name="M",
        admission_number=f"TST-{uid}-001", date_of_admission=date(2025,9,1),
        current_class_id=cls.id, status="active", gender="Male",
        date_of_birth=date(2015,1,1), home_address="123 Test St",
        parent_name="Jane Doe", parent_phone="08012345678",
    )
    db.add(student)
    db.flush()

    rec = AcademicRecord(
        student_id=student.id, class_subject_id=cs.id,
        term_id=term.id, score=85.0, max_score=100.0,
        recorded_by=staff.id, recorded_at=now,
    )
    db.add(rec)

    withdrawn_student = Student(
        first_name="Jane", last_name="Smith",
        admission_number=f"TST-{uid}-002",
        current_class_id=cls.id, status="withdrawn", gender="Female",
        date_of_birth=date(2015,3,1), parent_name="Bob Smith",
    )
    db.add(withdrawn_student)

    graduated_student = Student(
        first_name="Alice", last_name="Johnson",
        admission_number=f"TST-{uid}-003",
        current_class_id=cls.id, status="graduated", gender="Female",
        date_of_birth=date(2014,6,1), parent_name="Carol Johnson",
    )
    db.add(graduated_student)

    scale_a = GradingScale(grade="A", min_score=70.0, max_score=100.0, remark="Excellent")
    scale_b = GradingScale(grade="B", min_score=60.0, max_score=69.99, remark="Very Good")
    scale_c = GradingScale(grade="C", min_score=50.0, max_score=59.99, remark="Good")
    db.add_all([scale_a, scale_b, scale_c])

    db.commit()

    return {
        "uid": uid,
        "term_id": str(term.id),
        "class_id": str(cls.id),
        "student_id": str(student.id),
        "withdrawn_id": str(withdrawn_student.id),
        "graduated_id": str(graduated_student.id),
        "subject_id": str(subj.id),
        "cs_id": str(cs.id),
        "staff_id": str(staff.id),
        "scale_a_id": str(scale_a.id),
        "scale_b_id": str(scale_b.id),
        "scale_c_id": str(scale_c.id),
    }

def clean_data(db, ids: dict):
    """Remove test data."""
    for model in [
        AcademicRecord, Student, ClassSubject,
        Subject, SchoolClass, AcademicTerm, GradingScale, Staff,
    ]:
        db.query(model).delete()
    db.commit()

def main():
    db = SessionLocal()
    ids = None
    try:
        user = db.query(User).filter(User.email == "endpoint-test@test.com").first()
        if not user:
            user = User(
                id=uuid.uuid4(), email="endpoint-test@test.com",
                full_name="Endpoint Tester",
                password_hash=hash_password("testpass"),
                role="admin", is_active=True,
            )
            db.add(user)
            db.commit()

        ids = seed_data(db)
        print("Seed data created OK")
    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        import traceback; traceback.print_exc()
        return
    finally:
        db.close()

    app = create_app()
    client = TestClient(app)

    resp = client.post("/api/auth/login", json={"email": "endpoint-test@test.com", "password": "testpass"})
    assert resp.status_code == 200, f"Login failed: {resp.status_code} {resp.text}"
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\n{'='*60}")
    print(f"Login OK — token: {token[:20]}...")
    print(f"{'='*60}")

    passed = 0
    failed = 0

    def check(label, resp, expected_status=200):
        nonlocal passed, failed
        ok = resp.status_code == expected_status
        status = "OK" if ok else f"FAIL (expected {expected_status}, got {resp.status_code})"
        print(f"  [{status}] {label}")
        if not ok:
            print(f"         Response: {resp.text[:300]}")
            failed += 1
        else:
            passed += 1

    uid = ids["uid"]

    # --- 1. Grading Scales ---------------------------------------------
    print(f"\n--- Grading Scales ---")

    resp = client.get("/api/school/grading-scales", headers=headers)
    check("GET /grading-scales (list)", resp, 200)
    assert isinstance(resp.json(), list)

    resp = client.post("/api/school/grading-scales", headers=headers, json={
        "grade": "D", "min_score": 40.0, "max_score": 49.99, "remark": "Fair",
    })
    check("POST /grading-scales (create D)", resp, 201)
    d_id = resp.json().get("id", "")

    if d_id:
        resp = client.patch(f"/api/school/grading-scales/{d_id}", headers=headers, json={
            "remark": "Fair (needs improvement)",
        })
        check(f"PATCH /grading-scales/{d_id[:8]}", resp, 200)
        assert resp.json()["remark"] == "Fair (needs improvement)"

    if d_id:
        resp = client.delete(f"/api/school/grading-scales/{d_id}", headers=headers)
        check(f"DELETE /grading-scales/{d_id[:8]}", resp, 200)

    resp = client.get("/api/school/grading-info")
    check("GET /grading-info (public)", resp, 200)
    assert "scales" in resp.json()

    # --- 2. Report Card ------------------------------------------------
    print(f"\n--- Report Card ---")

    sid = ids["student_id"]
    tid = ids["term_id"]
    resp = client.get(f"/api/school/students/{sid}/report-card?term_id={tid}", headers=headers)
    check("GET /students/{id}/report-card", resp, 200)
    data = resp.json()
    assert data["student_name"] == "John Doe"
    assert data["admission_number"] == f"TST-{uid}-001"
    assert len(data["subjects"]) >= 1
    subj = data["subjects"][0]
    assert subj["subject_code"] == "MTH101"
    assert subj["score"] == 85.0
    assert subj["grade"] == "A"
    assert data["total_score"] == 85.0
    assert data["average"] == 85.0
    print(f"         Subjects: {len(data['subjects'])}, Avg: {data['average']}, Grade: {subj['grade']}")

    # --- 3. Transcript -------------------------------------------------
    print(f"\n--- Transcript ---")

    resp = client.get(f"/api/school/students/{sid}/transcript", headers=headers)
    check("GET /students/{id}/transcript", resp, 200)
    data = resp.json()
    assert data["student_name"] == "John Doe"
    assert len(data["terms"]) >= 1
    print(f"         Terms: {len(data['terms'])}, Subjects in term 1: {len(data['terms'][0]['subjects'])}")

    # --- 4. Outlist ----------------------------------------------------
    print(f"\n--- Outlist ---")

    resp = client.get("/api/school/students/outlist?status=withdrawn", headers=headers)
    check("GET /students/outlist?status=withdrawn", resp, 200)
    data = resp.json()
    assert "students" in data
    names = [s["last_name"] for s in data["students"]]
    assert "Smith" in names
    print(f"         Withdrawn: {len(data['students'])} student(s) — {names}")

    resp = client.get("/api/school/students/outlist?status=graduated", headers=headers)
    check("GET /students/outlist?status=graduated", resp, 200)
    names = [s["last_name"] for s in resp.json()["students"]]
    assert "Johnson" in names
    print(f"         Graduated: {len(resp.json()['students'])} student(s) — {names}")

    resp = client.get("/api/school/students/outlist?status=withdrawn,graduated", headers=headers)
    check("GET /students/outlist?status=withdrawn,graduated", resp, 200)
    print(f"         Combined: {len(resp.json()['students'])} student(s)")

    # --- Cleanup -------------------------------------------------------
    db2 = SessionLocal()
    try:
        clean_data(db2, ids)
        print(f"\n{'='*60}")
        print(f"RESULTS: {passed} passed, {failed} failed")
        print(f"{'='*60}")
    finally:
        db2.close()

    if failed:
        exit(1)

if __name__ == "__main__":
    main()
