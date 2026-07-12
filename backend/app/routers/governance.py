"""Governance module: ESG policies, acknowledgements, audits, and
compliance issues.

The append-only ESG ledger (GET /governance/ledger, /ledger/verify) is not
part of this pass and remains unimplemented.

Policies get a PATCH endpoint (full CRUD, as requested) beyond what
docs/CONTRACT.md documents (GET/POST only) — additive, not a rename of any
documented route. No DELETE is added anywhere in this router: hard-deleting
policies/audits/compliance history conflicts with governance/audit-trail
expectations, and CONTRACT.md doesn't call for it.
"""

from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.services_features.auth_dep import get_current_user_id
from app.services_features.lifecycle import COMPLIANCE_ISSUE_TRANSITIONS, is_legal_transition
from app.services_features.notifications_service import TYPE_COMPLIANCE, create_notification

router = APIRouter(prefix="/governance", tags=["governance"])

POLICY_COLUMNS = "id, title, body, version, category, is_mandatory, effective_date, created_at"
ACK_COLUMNS = "id, policy_id, user_id, acknowledged_at, ip_address"
AUDIT_COLUMNS = (
    "id, title, framework, scope, status, auditor_user_id, "
    "period_start, period_end, scheduled_date, completed_date, created_at"
)
CI_COLUMNS = (
    "id, audit_id, title, description, severity, status, "
    "owner_user_id, due_date, resolved_at, created_at"
)

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
AuditStatus = Literal["PLANNED", "IN_PROGRESS", "COMPLETED"]
ComplianceStatus = Literal["OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"]


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

class PolicyCreate(BaseModel):
    title: str
    body: str
    version: int = 1
    category: str | None = None
    is_mandatory: bool = True
    effective_date: date


class PolicyPatch(BaseModel):
    title: str | None = None
    body: str | None = None
    version: int | None = None
    category: str | None = None
    is_mandatory: bool | None = None
    effective_date: date | None = None


class AuditCreate(BaseModel):
    title: str
    framework: str | None = None
    scope: str | None = None
    status: AuditStatus = "PLANNED"
    auditor_user_id: int | None = None
    period_start: date | None = None
    period_end: date | None = None
    scheduled_date: date | None = None


class AuditPatch(BaseModel):
    title: str | None = None
    framework: str | None = None
    scope: str | None = None
    status: AuditStatus | None = None
    auditor_user_id: int | None = None
    period_start: date | None = None
    period_end: date | None = None
    scheduled_date: date | None = None
    completed_date: date | None = None


class ComplianceIssueCreate(BaseModel):
    audit_id: int | None = None
    title: str
    description: str | None = None
    severity: Severity = "MEDIUM"
    owner_user_id: int
    due_date: date


class ComplianceIssuePatch(BaseModel):
    audit_id: int | None = None
    title: str | None = None
    description: str | None = None
    severity: Severity | None = None
    status: ComplianceStatus | None = None
    owner_user_id: int | None = None
    due_date: date | None = None


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _policy_or_404(db: Session, policy_id: int) -> dict:
    row = db.execute(
        text(f"SELECT {POLICY_COLUMNS} FROM esg_policies WHERE id = :id"),
        {"id": policy_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")
    return dict(row)


def _audit_or_404(db: Session, audit_id: int) -> dict:
    row = db.execute(
        text(f"SELECT {AUDIT_COLUMNS} FROM audits WHERE id = :id"),
        {"id": audit_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audit not found")
    return dict(row)


def _compliance_issue_or_404(db: Session, issue_id: int) -> dict:
    row = db.execute(
        text(f"SELECT {CI_COLUMNS} FROM compliance_issues WHERE id = :id"),
        {"id": issue_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Compliance issue not found")
    return dict(row)


# --------------------------------------------------------------------------
# Policies
# --------------------------------------------------------------------------

@router.get("/policies")
def list_policies(
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> list[dict]:
    rows = db.execute(
        text(f"SELECT {POLICY_COLUMNS} FROM esg_policies ORDER BY effective_date DESC, id DESC")
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/policies", status_code=status.HTTP_201_CREATED)
def create_policy(
    body: PolicyCreate,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> dict:
    row = db.execute(
        text(
            f"""
            INSERT INTO esg_policies (title, body, version, category, is_mandatory, effective_date)
            VALUES (:title, :body, :version, :category, :is_mandatory, :effective_date)
            RETURNING {POLICY_COLUMNS}
            """
        ),
        body.model_dump(),
    ).mappings().first()
    db.commit()
    return dict(row)


@router.patch("/policies/{policy_id}")
def patch_policy(
    policy_id: int,
    body: PolicyPatch,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> dict:
    policy = _policy_or_404(db, policy_id)
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return policy

    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    row = db.execute(
        text(f"UPDATE esg_policies SET {set_clause} WHERE id = :id RETURNING {POLICY_COLUMNS}"),
        {**updates, "id": policy_id},
    ).mappings().first()
    db.commit()
    return dict(row)


# --------------------------------------------------------------------------
# Policy acknowledgements
# --------------------------------------------------------------------------

@router.post("/policies/{policy_id}/acknowledge", status_code=status.HTTP_201_CREATED)
def acknowledge_policy(
    policy_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
) -> dict:
    _policy_or_404(db, policy_id)
    try:
        row = db.execute(
            text(
                f"""
                INSERT INTO policy_acknowledgements (policy_id, user_id, ip_address)
                VALUES (:policy_id, :user_id, :ip_address)
                RETURNING {ACK_COLUMNS}
                """
            ),
            {
                "policy_id": policy_id,
                "user_id": current_user_id,
                "ip_address": request.client.host if request.client else None,
            },
        ).mappings().first()
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Policy already acknowledged")
    return dict(row)


@router.get("/policies/{policy_id}/acknowledgements")
def list_acknowledgements(
    policy_id: int,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> list[dict]:
    _policy_or_404(db, policy_id)
    rows = db.execute(
        text(f"SELECT {ACK_COLUMNS} FROM policy_acknowledgements WHERE policy_id = :id ORDER BY id"),
        {"id": policy_id},
    ).mappings().all()
    return [dict(row) for row in rows]


# --------------------------------------------------------------------------
# Audits
# --------------------------------------------------------------------------

@router.get("/audits")
def list_audits(
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> list[dict]:
    rows = db.execute(
        text(f"SELECT {AUDIT_COLUMNS} FROM audits ORDER BY scheduled_date DESC, id DESC")
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/audits", status_code=status.HTTP_201_CREATED)
def create_audit(
    body: AuditCreate,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> dict:
    row = db.execute(
        text(
            f"""
            INSERT INTO audits
                (title, framework, scope, status, auditor_user_id,
                 period_start, period_end, scheduled_date)
            VALUES
                (:title, :framework, :scope, :status, :auditor_user_id,
                 :period_start, :period_end, :scheduled_date)
            RETURNING {AUDIT_COLUMNS}
            """
        ),
        body.model_dump(),
    ).mappings().first()
    db.commit()
    return dict(row)


@router.patch("/audits/{audit_id}")
def patch_audit(
    audit_id: int,
    body: AuditPatch,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> dict:
    audit = _audit_or_404(db, audit_id)
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return audit

    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    row = db.execute(
        text(f"UPDATE audits SET {set_clause} WHERE id = :id RETURNING {AUDIT_COLUMNS}"),
        {**updates, "id": audit_id},
    ).mappings().first()
    db.commit()
    return dict(row)


# --------------------------------------------------------------------------
# Compliance issues
# --------------------------------------------------------------------------

@router.get("/compliance-issues")
def list_compliance_issues(
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> list[dict]:
    rows = db.execute(
        text(f"SELECT {CI_COLUMNS} FROM compliance_issues ORDER BY due_date, id")
    ).mappings().all()
    return [dict(row) for row in rows]


@router.post("/compliance-issues", status_code=status.HTTP_201_CREATED)
def create_compliance_issue(
    body: ComplianceIssueCreate,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> dict:
    row = db.execute(
        text(
            f"""
            INSERT INTO compliance_issues
                (audit_id, title, description, severity, owner_user_id, due_date)
            VALUES
                (:audit_id, :title, :description, :severity, :owner_user_id, :due_date)
            RETURNING {CI_COLUMNS}
            """
        ),
        body.model_dump(),
    ).mappings().first()

    create_notification(
        db,
        user_id=body.owner_user_id,
        title="Compliance issue raised",
        body=f'"{body.title}" ({body.severity}) is due {body.due_date.isoformat()}.',
        type_=TYPE_COMPLIANCE,
        link="/governance",
    )

    db.commit()
    return dict(row)


@router.patch("/compliance-issues/{issue_id}")
def patch_compliance_issue(
    issue_id: int,
    body: ComplianceIssuePatch,
    db: Session = Depends(get_db),
    _: int = Depends(get_current_user_id),
) -> dict:
    issue = _compliance_issue_or_404(db, issue_id)
    updates = body.model_dump(exclude_unset=True)

    if "status" in updates:
        current, target = issue["status"], updates["status"]
        if not is_legal_transition(COMPLIANCE_ISSUE_TRANSITIONS, current, target):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Illegal status transition: {current} -> {target}",
            )
        if target == "RESOLVED":
            updates["resolved_at"] = datetime.now(timezone.utc)
        elif current == "RESOLVED":
            updates["resolved_at"] = None

    if not updates:
        return issue

    set_clause = ", ".join(f"{field} = :{field}" for field in updates)
    row = db.execute(
        text(f"UPDATE compliance_issues SET {set_clause} WHERE id = :id RETURNING {CI_COLUMNS}"),
        {**updates, "id": issue_id},
    ).mappings().first()
    db.commit()
    return dict(row)
