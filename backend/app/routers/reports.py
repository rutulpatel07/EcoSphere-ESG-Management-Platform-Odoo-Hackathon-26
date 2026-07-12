"""Reports module: 4 canned summary generators (env/social/gov/esg) plus an
additive custom cross-module report, exported as CSV (native csv module),
Excel (openpyxl), or PDF (reportlab) — all local libraries already in
requirements.txt.

POST /reports/custom is not documented in docs/CONTRACT.md (only
available/generate/recent are); it's kept as a separate endpoint rather
than changing the documented /reports/generate request shape.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db import get_db
from app.models import User
from app.services_features import reports_history
from app.services_features.exporters import to_csv, to_pdf, to_xlsx
from app.services_features.reports_data import REPORT_DEFINITIONS, custom_report, parse_period

router = APIRouter(prefix="/reports", tags=["reports"])

_MIME_TYPES = {
    "PDF": "application/pdf",
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "CSV": "text/csv",
}
_EXTENSIONS = {"PDF": "pdf", "XLSX": "xlsx", "CSV": "csv"}


def _render(columns: list[str], rows: list[dict], name: str, fmt: str) -> bytes:
    fmt = fmt.upper()
    if fmt == "CSV":
        return to_csv(columns, rows)
    if fmt == "XLSX":
        return to_xlsx(columns, rows)
    if fmt == "PDF":
        return to_pdf(name, columns, rows)
    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported format: {fmt}")


def _file_response(content: bytes, name: str, fmt: str) -> Response:
    fmt = fmt.upper()
    filename = f"{name.replace(' ', '_')}.{_EXTENSIONS[fmt]}"
    return Response(
        content=content,
        media_type=_MIME_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    report_id: str
    format: str
    period: str | None = None


class CustomReportRequest(BaseModel):
    department_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    module: str | None = None
    employee_id: int | None = None
    challenge_id: int | None = None
    esg_category: str | None = None
    format: str = "PDF"


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

@router.get("/available")
def list_available(_: User = Depends(get_current_user)) -> list[dict]:
    return [
        {"id": report_id, "name": meta["name"], "formats": ["PDF", "XLSX", "CSV"]}
        for report_id, meta in REPORT_DEFINITIONS.items()
    ]


@router.post("/generate")
def generate(
    body: GenerateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Response:
    meta = REPORT_DEFINITIONS.get(body.report_id)
    if meta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown report_id: {body.report_id}")

    start, end = parse_period(body.period)
    columns, rows = meta["builder"](db, start, end)
    content = _render(columns, rows, meta["name"], body.format)
    reports_history.record(name=meta["name"], format=body.format.upper(), size_bytes=len(content))
    return _file_response(content, meta["name"], body.format)


@router.get("/recent")
def recent(_: User = Depends(get_current_user)) -> list[dict]:
    return reports_history.recent()


@router.post("/custom")
def generate_custom(
    body: CustomReportRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Response:
    columns, rows = custom_report(
        db,
        department_id=body.department_id,
        start_date=body.start_date,
        end_date=body.end_date,
        module=body.module.upper() if body.module else None,
        employee_id=body.employee_id,
        challenge_id=body.challenge_id,
        esg_category=body.esg_category.upper() if body.esg_category else None,
    )
    name = "Custom ESG Report"
    content = _render(columns, rows, name, body.format)
    reports_history.record(name=name, format=body.format.upper(), size_bytes=len(content))
    return _file_response(content, name, body.format)
