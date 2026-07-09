from __future__ import annotations
import json
import re
from typing import Optional
from pydantic import BaseModel, Field


class ParsedTopic(BaseModel):
    title: str
    content: str = ""
    week_number: Optional[int] = None
    sort_order: int = 0
    children: list[ParsedTopic] = Field(default_factory=list)


class ParsedSyllabus(BaseModel):
    format: str
    topic_count: int
    content_length: int
    topics: list[ParsedTopic]


ParsedTopic.model_rebuild()
ParsedSyllabus.model_rebuild()


def parse_json(file_bytes: bytes) -> ParsedSyllabus:
    data = json.loads(file_bytes.decode("utf-8"))
    topics = data if isinstance(data, list) else data.get("topics", [])
    parsed = [_parse_json_topic(t, i) for i, t in enumerate(topics)]
    return ParsedSyllabus(
        format="json",
        topic_count=len(parsed),
        content_length=sum(len(t.content) for t in _flatten(parsed)),
        topics=parsed,
    )


def _parse_json_topic(t: dict, idx: int) -> ParsedTopic:
    children = [_parse_json_topic(c, i) for i, c in enumerate(t.get("subtopics", t.get("children", [])))]
    return ParsedTopic(
        title=t["title"],
        content=t.get("content", ""),
        week_number=t.get("week"),
        sort_order=idx,
        children=children,
    )


def _flatten(topics: list[ParsedTopic]) -> list[ParsedTopic]:
    result = []
    for t in topics:
        result.append(t)
        result.extend(_flatten(t.children))
    return result


def parse_docx(file_bytes: bytes) -> ParsedSyllabus:
    from docx import Document
    import io

    doc = Document(io.BytesIO(file_bytes))
    root_topics: list[ParsedTopic] = []
    stack: list[ParsedTopic] = []
    body_text: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        style_name = para.style.name if para.style else ""
        is_heading = style_name.startswith("Heading") if style_name else False

        if is_heading:
            level_match = re.search(r"(\d+)", style_name)
            level = int(level_match.group(1)) if level_match else 1

            if body_text:
                _add_body_text(stack, body_text)
                body_text = []

            topic = ParsedTopic(title=text, content="", children=[])
            while stack and len(stack) >= level:
                stack.pop()
            if stack:
                stack[-1].children.append(topic)
            else:
                root_topics.append(topic)
            stack.append(topic)
        else:
            body_text.append(text)

    if body_text:
        _add_body_text(stack, body_text)

    _assign_sort_order(root_topics)

    return ParsedSyllabus(
        format="docx",
        topic_count=len(list(_flatten(root_topics))),
        content_length=sum(len(t.content) for t in _flatten(root_topics)),
        topics=root_topics,
    )


def _add_body_text(stack: list[ParsedTopic], lines: list[str]) -> None:
    text = "<p>" + "</p><p>".join(lines) + "</p>"
    if stack:
        cur = stack[-1]
        cur.content = (cur.content + text) if cur.content else text


def _assign_sort_order(topics: list[ParsedTopic], parent_idx: int = 0) -> None:
    for i, t in enumerate(topics):
        t.sort_order = i
        _assign_sort_order(t.children, i)


def parse_pdf(file_bytes: bytes) -> ParsedSyllabus:
    import fitz

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    root_topics: list[ParsedTopic] = []
    stack: list[ParsedTopic] = []
    font_sizes: list[float] = []

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    size = span["size"]
                    font_sizes.append(size)

    if not font_sizes:
        return ParsedSyllabus(format="pdf", topic_count=0, content_length=0, topics=[])

    font_sizes.sort(reverse=True)
    threshold = font_sizes[len(font_sizes) // 4] if len(font_sizes) > 4 else font_sizes[0]

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        body_buf: list[str] = []
        for block in blocks:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    size = span["size"]
                    if size >= threshold:
                        if body_buf:
                            _add_body_text(stack, body_buf)
                            body_buf = []
                        topic = ParsedTopic(title=text, content="", children=[])
                        stack.clear()
                        stack.append(topic)
                        root_topics.append(topic)
                    else:
                        body_buf.append(text)
        if body_buf:
            _add_body_text(stack, body_buf)

    _assign_sort_order(root_topics)

    return ParsedSyllabus(
        format="pdf",
        topic_count=len(list(_flatten(root_topics))),
        content_length=sum(len(t.content) for t in _flatten(root_topics)),
        topics=root_topics,
    )


def detect_format(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {"json": "json", "doc": "docx", "docx": "docx", "pdf": "pdf"}.get(ext, "")


def parse_syllabus(file_bytes: bytes, filename: str) -> ParsedSyllabus:
    fmt = detect_format(filename)
    if fmt == "json":
        return parse_json(file_bytes)
    elif fmt == "docx":
        return parse_docx(file_bytes)
    elif fmt == "pdf":
        return parse_pdf(file_bytes)
    raise ValueError(f"Unsupported file format: {filename}")
