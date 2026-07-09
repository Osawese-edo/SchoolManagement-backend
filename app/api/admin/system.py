import json
from datetime import datetime, date, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.session import get_db, Base
from app.core.exceptions import AppException, NotFoundException, BadRequestException
from app.core.rate_limit import limiter
from app.core.dependencies import require_role
from app.models.user import User
from app.services.log_helper import log_action


router = APIRouter()


class ExportRequest(BaseModel):
    tables: list[str]


class DeleteRequest(BaseModel):
    tables: list[str]
    confirm: bool = Field(False, description="Must be true to execute deletion")


def _build_dependency_graph() -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for table_name, table in Base.metadata.tables.items():
        deps: set[str] = set()
        for fk in table.foreign_keys:
            ref_table = fk.column.table.name
            if ref_table != table_name:
                deps.add(ref_table)
        graph[table_name] = deps
    return graph


def _build_cascade_graph() -> dict[str, list[str]]:
    """For each table, which tables will be cascade-deleted when it's deleted."""
    graph: dict[str, list[str]] = {}
    for table_name, table in Base.metadata.tables.items():
        if table_name.startswith("alembic_"):
            continue
        children: list[str] = []
        for other_name, other_table in Base.metadata.tables.items():
            for fk in other_table.foreign_keys:
                if fk.column.table.name == table_name and fk.ondelete == "CASCADE":
                    children.append(other_name)
        if children:
            graph[table_name] = sorted(set(children))
    return graph


def _cascade_descendants(tables: list[str], graph: dict[str, list[str]]) -> list[str]:
    """All cascade descendants (recursive) for the given tables."""
    result: list[str] = []
    visited: set[str] = set()
    def walk(names: list[str]):
        for name in names:
            if name in visited:
                continue
            visited.add(name)
            children = graph.get(name, [])
            result.extend(children)
            walk(children)
    walk(tables)
    return result


def _topological_sort(tables: list[str], graph: dict[str, set[str]]) -> list[str]:
    selected = set(tables)
    subgraph = {t: graph[t] & selected for t in tables}
    in_degree = {t: len(deps) for t, deps in subgraph.items()}
    queue = [t for t in tables if in_degree[t] == 0]
    result: list[str] = []
    while queue:
        node = queue.pop(0)
        result.append(node)
        for other in tables:
            if node in subgraph.get(other, set()):
                in_degree[other] -= 1
                if in_degree[other] == 0:
                    queue.append(other)
    for t in tables:
        if t not in result:
            result.append(t)
    return result


def _reverse_topological_sort(tables: list[str], graph: dict[str, set[str]]) -> list[str]:
    return list(reversed(_topological_sort(tables, graph)))


def _serialize_row(row) -> dict:
    return {
        k: _serialize_value(v)
        for k, v in row._mapping.items()
    }


def _serialize_value(val):
    if isinstance(val, UUID):
        return str(val)
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return val.isoformat()
    return val


@router.get("/system/tables")
@limiter.limit("120/minute")
def list_tables(
    request: Request,
    include_deps: bool = Query(False),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    result = []
    for table_name, table in Base.metadata.tables.items():
        if table_name.startswith("alembic_"):
            continue
        table_obj = Base.metadata.tables.get(table_name)
        if not table_obj:
            raise NotFoundException(detail="Unknown table")
        count = db.query(func.count()).select_from(table_obj).scalar()
        result.append({"name": table_name, "row_count": count})
    response: dict = {"tables": result}
    if include_deps:
        response["cascade_graph"] = _build_cascade_graph()
    return response


@router.post("/system/export")
@limiter.limit("10/minute")
def export_data(
    request: Request,
    data: ExportRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    tables = data.tables
    if not tables:
        return {"exported_at": datetime.now(timezone.utc).isoformat(), "tables": {}}

    graph = _build_dependency_graph()
    ordered = _topological_sort(tables, graph)

    exported: dict[str, list[dict]] = {}
    for table_name in ordered:
        table = Base.metadata.tables.get(table_name)
        if not table:
            raise NotFoundException(detail="Unknown table")
        rows = db.execute(table.select()).all()
        exported[table_name] = [_serialize_row(row) for row in rows]

    log_action(db, current_user, f"Exported tables: {', '.join(tables)}", "system")
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tables": exported,
    }


@router.post("/system/import")
@limiter.limit("10/minute")
def import_data(
    request: Request,
    file: UploadFile = File(...),
    tables: list[str] = Form([]),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    try:
        content = json.loads(file.file.read())
    except Exception:
        raise BadRequestException(detail="Invalid JSON file")

    if "tables" not in content:
        raise BadRequestException(detail="JSON must contain a 'tables' key")

    graph = _build_dependency_graph()
    ordered = _topological_sort(tables, graph)

    results: list[dict] = []
    try:
        for table_name in ordered:
            rows = content["tables"].get(table_name, [])
            if not rows:
                results.append({"table": table_name, "inserted": 0, "skipped": 0})
                continue

            table_obj = Base.metadata.tables[table_name]
            pks = list(table_obj.primary_key.columns)
            pk_column = pks[0].name if pks else "id"

            inserted = 0
            skipped = 0

            for row in rows:
                cleaned = {}
                for k, v in row.items():
                    if v == "" or v is None:
                        cleaned[k] = None
                    else:
                        cleaned[k] = v

                stmt = pg_insert(table_obj).values(**cleaned).on_conflict_do_nothing(index_elements=[pk_column])
                result = db.execute(stmt)
                if result.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1

            results.append({"table": table_name, "inserted": inserted, "skipped": skipped})

        db.commit()
        log_action(db, current_user, f"Imported {sum(r['inserted'] for r in results)} rows into {', '.join(tables)}", "system")
    except Exception:
        db.rollback()
        raise BadRequestException(detail="Import failed")

    return {"results": results}


@router.post("/system/delete")
@limiter.limit("30/minute")
def delete_data(
    request: Request,
    data: DeleteRequest,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    tables = data.tables
    if not tables:
        return {"results": []}

    graph = _build_dependency_graph()
    ordered = _reverse_topological_sort(tables, graph)

    if not data.confirm:
        raise BadRequestException(detail="Set 'confirm' to true to execute deletion")

    results: list[dict] = []
    try:
        for table_name in ordered:
            table_obj = Base.metadata.tables.get(table_name)
            if not table_obj:
                raise NotFoundException(detail="Unknown table")
            count = db.execute(table_obj.delete()).rowcount
            results.append({"table": table_name, "deleted": count})
        db.commit()
        log_action(db, current_user, f"Deleted data from tables: {', '.join(tables)}", "system")
    except Exception:
        db.rollback()
        raise BadRequestException(detail="Delete failed")

    return {"results": results}
