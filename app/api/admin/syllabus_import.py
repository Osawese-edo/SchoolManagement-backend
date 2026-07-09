from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limit import limiter
from app.core.dependencies import require_role
from app.models.user import User
from app.models.subject import Subject
from app.models.class_subject import ClassSubject
from app.models.school_class import SchoolClass
from app.models.syllabus_topic import SyllabusTopic
from app.models.academic_term import AcademicTerm
from app.models.syllabus_document import SyllabusDocument
from app.services.upload_service import UploadService
from app.services.syllabus_parser import parse_syllabus, ParsedTopic, ParsedSyllabus

router = APIRouter()


class ParsedTopicOut(BaseModel):
    title: str
    content: str = ""
    week_number: int | None = None
    sort_order: int = 0
    children: list[ParsedTopicOut] = Field(default_factory=list)
    match_status: str = "new"
    match_id: str | None = None


ParsedTopicOut.model_rebuild()


class PreviewResponse(BaseModel):
    format: str
    topic_count: int
    content_length: int
    topics: list[ParsedTopicOut]
    existing_document: bool = False
    file_is_pdf: bool = False


class ImportResultItem(BaseModel):
    title: str
    status: str
    id: str | None = None


class ImportResponse(BaseModel):
    created: int
    skipped: int
    results: list[ImportResultItem]
    document_saved: bool = False


MAX_FILE_SIZE = 20 * 1024 * 1024


def _build_topic_out(t: ParsedTopic, existing_map: dict[str, list[dict]]) -> ParsedTopicOut:
    key = t.title.strip().upper()
    matches = existing_map.get(key, [])
    status = "new"
    match_id = None
    if matches:
        status = "match"
        match_id = matches[0]["id"]
    return ParsedTopicOut(
        title=t.title,
        content=t.content,
        week_number=t.week_number,
        sort_order=t.sort_order,
        children=[_build_topic_out(c, existing_map) for c in t.children],
        match_status=status,
        match_id=match_id,
    )


def _flatten_parsed(topics: list[ParsedTopic]) -> list[ParsedTopic]:
    result = []
    for t in topics:
        result.append(t)
        result.extend(_flatten_parsed(t.children))
    return result


def _get_existing_titles(db: Session, class_subject_id: UUID | None, subject_id: UUID | None, term_id: UUID) -> dict[str, list[dict]]:
    q = db.query(SyllabusTopic).filter(SyllabusTopic.term_id == term_id)
    if class_subject_id:
        q = q.filter(SyllabusTopic.class_subject_id == class_subject_id)
    if subject_id:
        q = q.filter(SyllabusTopic.subject_id == subject_id)
    topics = q.all()
    mapping: dict[str, list[dict]] = {}
    for t in topics:
        key = t.title.strip().upper()
        mapping.setdefault(key, []).append({"id": str(t.id)})
    return mapping


def _resolve_class_subject(db: Session, class_id: UUID, subject_id: UUID) -> ClassSubject:
    cs = db.query(ClassSubject).filter(
        ClassSubject.class_id == class_id,
        ClassSubject.subject_id == subject_id,
    ).first()
    if cs:
        return cs
    cs = ClassSubject(class_id=class_id, subject_id=subject_id, max_score=100)
    db.add(cs)
    db.flush()
    return cs


def _ensure_subject(db: Session, name: str, code: str | None = None) -> Subject:
    subj_code = code or name.upper().replace(" ", "-")[:20]
    subj = db.query(Subject).filter(
        (Subject.code == subj_code) | (Subject.name == name)
    ).first()
    if subj:
        return subj
    subj = Subject(name=name, code=subj_code)
    db.add(subj)
    db.flush()
    return subj


def _create_syllabus_topics(
    db: Session,
    topics: list[ParsedTopic],
    class_subject_id: UUID | None,
    subject_id: UUID | None,
    term_id: UUID,
    allowed_titles: set[str],
    parent_id: UUID | None = None,
) -> list[dict]:
    results = []
    for t in topics:
        key = t.title.strip().upper()
        if key not in allowed_titles:
            results.append({"title": t.title, "status": "skipped"})
            continue
        topic = SyllabusTopic(
            class_subject_id=class_subject_id,
            subject_id=subject_id,
            term_id=term_id,
            parent_id=parent_id,
            title=t.title,
            content=t.content or "",
            week_number=t.week_number,
            sort_order=t.sort_order,
        )
        db.add(topic)
        db.flush()
        children_results = _create_syllabus_topics(
            db, t.children, class_subject_id, subject_id, term_id, allowed_titles, parent_id=topic.id,
        )
        results.append({"title": t.title, "status": "created", "id": str(topic.id)})
        results.extend(children_results)
    return results


@router.post("/syllabus/import/preview", response_model=None)
async def preview_syllabus_import(
    file: UploadFile = File(...),
    class_id: str = Form(...),
    subject_name: str = Form(...),
    term_id: str = Form(...),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 20MB)")

    filename = file.filename or "syllabus.json"
    try:
        parsed = parse_syllabus(content, filename)
    except Exception:
        raise HTTPException(400, "Failed to parse syllabus")

    term_uuid = UUID(term_id)
    class_uuid = UUID(class_id)

    existing_subject = _ensure_subject(db, subject_name)
    subj_id = existing_subject.id if existing_subject else None

    class_subject_id = None
    if existing_subject:
        cs = db.query(ClassSubject).filter(
            ClassSubject.class_id == class_uuid,
            ClassSubject.subject_id == subj_id,
        ).first()
        if cs:
            class_subject_id = cs.id

    existing_map = _get_existing_titles(db, class_subject_id, subj_id, term_uuid)
    topics_out = [_build_topic_out(t, existing_map) for t in parsed.topics]

    existing_doc = False
    if class_subject_id:
        existing_doc = db.query(SyllabusDocument).filter(
            SyllabusDocument.class_subject_id == class_subject_id
        ).first() is not None

    return PreviewResponse(
        format=parsed.format,
        topic_count=parsed.topic_count,
        content_length=parsed.content_length,
        topics=topics_out,
        existing_document=existing_doc,
        file_is_pdf=filename.lower().endswith(".pdf"),
    )


@router.post("/syllabus/import", response_model=None)
async def execute_syllabus_import(
    file: UploadFile = File(...),
    class_id: str = Form(...),
    subject_name: str = Form(...),
    term_id: str = Form(...),
    allowed_titles: str = Form(...),
    save_as_pdf: bool = Form(False),
    overwrite_pdf: bool = Form(False),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 20MB)")

    filename = file.filename or "syllabus.json"
    try:
        parsed = parse_syllabus(content, filename)
    except Exception:
        raise HTTPException(400, "Failed to parse syllabus")

    term_uuid = UUID(term_id)
    class_uuid = UUID(class_id)

    subject = _ensure_subject(db, subject_name)
    class_subject = _resolve_class_subject(db, class_uuid, subject.id)
    allowed = set(json.loads(allowed_titles)) if isinstance(allowed_titles, str) else set(allowed_titles)

    results = _create_syllabus_topics(
        db, parsed.topics,
        class_subject_id=class_subject.id,
        subject_id=subject.id,
        term_id=term_uuid,
        allowed_titles=allowed,
    )

    db.commit()

    created = sum(1 for r in results if r["status"] == "created")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    document_saved = False

    if save_as_pdf and filename.lower().endswith(".pdf"):
        if overwrite_pdf or not db.query(SyllabusDocument).filter(
            SyllabusDocument.class_subject_id == class_subject.id
        ).first():
            upload_svc = UploadService()
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            safe_name = f"syllabus/{class_subject.id}_{ts}.pdf"
            file_url, _ = upload_svc.upload(content, safe_name, "application/pdf")

            existing = db.query(SyllabusDocument).filter(
                SyllabusDocument.class_subject_id == class_subject.id
            ).first()
            if existing:
                db.delete(existing)
                db.flush()

            doc = SyllabusDocument(
                class_subject_id=class_subject.id,
                file_url=file_url,
                original_filename=filename,
                uploaded_at=datetime.now(timezone.utc),
            )
            db.add(doc)
            db.commit()
            document_saved = True

    return ImportResponse(created=created, skipped=skipped, results=results, document_saved=document_saved)
