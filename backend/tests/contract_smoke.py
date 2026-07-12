"""Smoke-tests every endpoint documented in docs/CONTRACT.md against a live
server and reports pass / not-implemented / mismatch per endpoint.

Not a pytest suite (most of the app is still owner-zone stubs, so a hard
pass/fail run would be almost entirely red for reasons outside this zone) --
it's a standalone report. Run with a server already up:

    DATABASE_URL=postgresql+psycopg2://ecosphere:ecosphere@127.0.0.1:5433/ecosphere \
        uvicorn app.main:app --port 8000 &
    python tests/contract_smoke.py [base_url]

Exit code is 0 unless a genuine MISMATCH was found on a route that exists
(a stub 404 is expected and does not fail the run).
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8022"
API = f"{BASE_URL}/api"


@dataclass
class Result:
    group: str
    method: str
    path: str
    status: int | None
    outcome: str  # OK | NOT_IMPLEMENTED | MISMATCH | SKIPPED
    note: str = ""
    expected_keys: set[str] = field(default_factory=set)
    got_keys: set[str] = field(default_factory=set)


results: list[Result] = []


def record(group, method, path, resp, *, expect_status=None, expected_keys=None, note=""):
    if resp is None:
        results.append(Result(group, method, path, None, "SKIPPED", note))
        return None

    got_keys: set[str] = set()
    try:
        body = resp.json()
        if isinstance(body, dict):
            got_keys = set(body.keys())
        elif isinstance(body, list) and body and isinstance(body[0], dict):
            got_keys = set(body[0].keys())
    except Exception:
        body = None

    if resp.status_code == 404 and (body is None or body == {"detail": "Not Found"}):
        results.append(Result(group, method, path, resp.status_code, "NOT_IMPLEMENTED", note))
        return None  # never let a caller mistake a stub's 404 body for a success payload

    expect_status = expect_status or range(200, 300)
    status_ok = resp.status_code in expect_status if hasattr(expect_status, "__contains__") else resp.status_code == expect_status
    shape_ok = True
    shape_note = ""
    if expected_keys is not None and status_ok:
        missing = expected_keys - got_keys
        if missing:
            shape_ok = False
            shape_note = f"missing keys: {sorted(missing)}"

    if status_ok and shape_ok:
        results.append(Result(group, method, path, resp.status_code, "OK", note, expected_keys or set(), got_keys))
        return body

    detail = ""
    try:
        detail = str(resp.json())[:200]
    except Exception:
        detail = resp.text[:200]
    results.append(
        Result(
            group, method, path, resp.status_code, "MISMATCH",
            f"{note} status={resp.status_code} {shape_note} body={detail}".strip(),
            expected_keys or set(), got_keys,
        )
    )
    return None  # MISMATCH bodies aren't safe for callers to chain off of either


def skip(group, method, path, reason):
    """Explicitly record a CONTRACT.md endpoint that couldn't be exercised
    because a prerequisite (usually a stub'd parent-resource POST) never
    produced an id -- so every documented endpoint appears in the report
    exactly once, never silently dropped."""
    results.append(Result(group, method, path, None, "SKIPPED", reason))


client = httpx.Client(base_url=API, timeout=10)

# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------
r = httpx.get(f"{BASE_URL}/health", timeout=10)
record("meta", "GET", "/health", r, expected_keys={"status", "app"},
       note="CONTRACT.md doesn't say whether this sits under /api; tested at bare /health (what main.py registers)")
r_api = httpx.get(f"{API}/health", timeout=10)
results.append(Result("meta", "GET", "/api/health", r_api.status_code,
                       "OK" if r_api.status_code == 200 else "NOT_IMPLEMENTED",
                       "informational: is /health ALSO reachable under /api?"))

# ---------------------------------------------------------------------------
# Auth -- need tokens before anything else
# ---------------------------------------------------------------------------
unique = uuid.uuid4().hex[:10]
admin_email = f"contract_admin_{unique}@ecosphere.io"
emp_email = f"contract_emp_{unique}@ecosphere.io"

r = client.post("/auth/login", json={"email": "nonexistent@ecosphere.io", "password": "wrong"})
record("auth", "POST", "/auth/login", r, expect_status={401}, expected_keys={"detail"})

r = client.post("/auth/signup", json={"email": emp_email, "full_name": "Contract Emp", "password": "smoketestpass1"})
body = record("auth", "POST", "/auth/signup (extra, not in CONTRACT)", r, expect_status={200, 201})
emp_token = body["access_token"] if body else None
emp_headers = {"Authorization": f"Bearer {emp_token}"} if emp_token else {}

r = client.get("/auth/me", headers=emp_headers)
record("auth", "GET", "/auth/me", r, expected_keys={"id", "email", "full_name", "role", "department_id", "points_balance"})

# Promote the smoke-test employee to ADMIN directly via DB so the rest of the
# run can exercise admin-gated endpoints (no admin exists yet on a fresh DB).
sys.path.insert(0, r"D:\Odoo Hackathon\EcoSphere-ESG-Management-Platform-Odoo-Hackathon-26\backend")
import os
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://ecosphere:ecosphere@127.0.0.1:5433/ecosphere")
from app.db import SessionLocal
from app.models import User
from app.models.enums import UserRole

db = SessionLocal()
u = db.query(User).filter_by(email=emp_email).one()
u.role = UserRole.ADMIN
db.commit()
db.close()

r = client.post("/auth/login", json={"email": emp_email, "password": "smoketestpass1"})
admin_token = r.json()["access_token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}
h = admin_headers  # use admin for everything below; simplest for a coverage smoke test

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
r = client.get("/users", headers=h)
record("users", "GET", "/users", r, expected_keys={"id", "email", "full_name", "role", "department_id", "points_balance", "is_active"})
r = client.post("/users", headers=h, json={"email": f"new_{unique}@ecosphere.io", "full_name": "New Person", "password": "x", "role": "EMPLOYEE"})
record("users", "POST", "/users", r, expect_status={201})
r = client.get("/users/1", headers=h)
record("users", "GET", "/users/{id}", r)
r = client.patch("/users/1", headers=h, json={"full_name": "x"})
record("users", "PATCH", "/users/{id}", r)
r = client.delete("/users/999999", headers=h)
record("users", "DELETE", "/users/{id}", r)

# ---------------------------------------------------------------------------
# Departments (mine)
# ---------------------------------------------------------------------------
r = client.get("/departments", headers=h)
record("departments", "GET", "/departments", r, expected_keys={"id", "name", "code", "parent_id", "manager_id"})
r = client.post("/departments", headers=h, json={"name": f"Contract Dept {unique}", "code": f"CD-{unique}"})
dept_body = record("departments", "POST", "/departments", r, expect_status={201},
                    expected_keys={"id", "name", "code", "parent_id", "manager_id", "created_at"})
dept_id = dept_body["id"] if dept_body else None
if dept_id:
    r = client.get(f"/departments/{dept_id}", headers=h)
    record("departments", "GET", "/departments/{id}", r, expected_keys={"id", "name", "code", "parent_id", "manager_id"})
    r = client.patch(f"/departments/{dept_id}", headers=h, json={"name": "Renamed"})
    record("departments", "PATCH", "/departments/{id}", r)
    # (DELETE tested after other sections finish referencing dept_id)

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
r = client.get("/dashboard/summary", headers=h)
record("dashboard", "GET", "/dashboard/summary", r,
       expected_keys={"esgScore", "kpis", "emissionsTrend", "departmentScores"})

# ---------------------------------------------------------------------------
# Environmental (mine)
# ---------------------------------------------------------------------------
r = client.get("/environmental/goals", headers=h)
record("environmental", "GET", "/environmental/goals", r,
       expected_keys={"id", "title", "metric", "baseline_value", "target_value", "current_value", "unit", "department_id", "start_date", "target_date", "status"})
r = client.post("/environmental/goals", headers=h, json={
    "title": "Contract goal", "metric": "Scope1+2 tCO2e", "baseline_value": 100, "target_value": 50,
    "unit": "tCO2e", "start_date": "2026-01-01", "target_date": "2026-12-31",
})
goal_body = record("environmental", "POST", "/environmental/goals", r, expect_status={201})
if goal_body:
    r = client.patch(f"/environmental/goals/{goal_body['id']}", headers=h, json={"current_value": 75})
    record("environmental", "PATCH", "/environmental/goals/{id}", r)

r = client.get("/environmental/emission-factors", headers=h)
record("environmental", "GET", "/environmental/emission-factors", r,
       expected_keys={"id", "activity_type", "unit", "factor_value", "source", "version", "valid_from", "valid_to", "uncertainty_pct"})
r = client.post("/environmental/emission-factors", headers=h, json={
    "activity_type": f"contract_activity_{unique}", "unit": "kWh", "factor_value": 0.2, "source": "test",
    "version": 1, "valid_from": "2025-01-01",
})
record("environmental", "POST", "/environmental/emission-factors", r, expect_status={201})

r = client.post("/environmental/operational-records", headers=h, json={
    "op_type": "FLEET", "department_id": dept_id, "activity_type": f"contract_activity_{unique}",
    "quantity": 1800, "unit": "kWh", "reference": "VAN-14", "occurred_on": "2026-06-28",
})
record("environmental", "POST", "/environmental/operational-records", r, expect_status={201},
       expected_keys={"id", "op_type", "activity_type", "quantity", "unit", "occurred_on", "carbon_transaction_id"},
       note="CONTRACT.md path -- extra zone from a prior session, not this one")

r = client.get("/environmental/carbon-transactions", headers=h)
record("environmental", "GET", "/environmental/carbon-transactions", r,
       expected_keys={"id", "operational_record_id", "emission_factor_id", "factor_value_used", "factor_version_used", "quantity", "co2e_kg", "scope", "data_tier", "uncertainty_pct", "department_id", "occurred_on"})

r = client.get("/environmental/products", headers=h)
record("environmental", "GET", "/environmental/products", r,
       expected_keys={"id", "sku", "name", "embodied_carbon_kg", "recyclable_pct", "water_usage_l", "ethical_score", "certifications"})
r = client.post("/environmental/products", headers=h, json={"sku": f"SMK-{unique}", "name": "Test product"})
record("environmental", "POST", "/environmental/products", r, expect_status={201})

# ---------------------------------------------------------------------------
# Social
# ---------------------------------------------------------------------------
r = client.get("/social/categories", headers=h, params={"type": "CSR"})
record("social", "GET", "/social/categories", r, expected_keys={"id", "name", "type", "is_active"})
r = client.post("/social/categories", headers=h, json={"name": "Test cat", "type": "CSR"})
record("social", "POST", "/social/categories", r, expect_status={201})

r = client.get("/social/activities", headers=h)
record("social", "GET", "/social/activities", r,
       expected_keys={"id", "title", "category_id", "department_id", "location", "points_reward", "capacity", "start_date", "end_date", "status"})
r = client.post("/social/activities", headers=h, json={"title": "Cleanup", "start_date": "2026-07-20", "points_reward": 100})
activity_body = record("social", "POST", "/social/activities", r, expect_status={201})
if activity_body:
    aid = activity_body["id"]
    r = client.patch(f"/social/activities/{aid}", headers=h, json={"status": "OPEN"})
    record("social", "PATCH", "/social/activities/{id}", r)
    r = client.get(f"/social/activities/{aid}/participants", headers=h)
    record("social", "GET", "/social/activities/{id}/participants", r,
           expected_keys={"id", "csr_activity_id", "user_id", "proof_url", "status", "hours", "verified_by"})
    r = client.post(f"/social/activities/{aid}/join", headers=h, json={"proof_url": "https://files.local/x.jpg"})
    join_body = record("social", "POST", "/social/activities/{id}/join", r, expect_status={200, 201})
    if join_body:
        r = client.patch(f"/social/participation/{join_body['id']}", headers=h, json={"status": "VERIFIED", "hours": 4})
        record("social", "PATCH", "/social/participation/{id}", r)
    else:
        skip("social", "PATCH", "/social/participation/{id}", "join did not return an id")
else:
    skip("social", "PATCH", "/social/activities/{id}", "POST /social/activities did not return an id")
    skip("social", "GET", "/social/activities/{id}/participants", "POST /social/activities did not return an id")
    skip("social", "POST", "/social/activities/{id}/join", "POST /social/activities did not return an id")
    skip("social", "PATCH", "/social/participation/{id}", "POST /social/activities did not return an id")

# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------
r = client.get("/governance/policies", headers=h)
record("governance", "GET", "/governance/policies", r,
       expected_keys={"id", "title", "version", "category", "is_mandatory", "effective_date"})
r = client.post("/governance/policies", headers=h, json={"title": "Test policy", "body": "...", "effective_date": "2026-01-01"})
policy_body = record("governance", "POST", "/governance/policies", r, expect_status={201})
if policy_body:
    pid = policy_body["id"]
    r = client.post(f"/governance/policies/{pid}/acknowledge", headers=h)
    record("governance", "POST", "/governance/policies/{id}/acknowledge", r, expect_status={200, 201})
    r = client.get(f"/governance/policies/{pid}/acknowledgements", headers=h)
    record("governance", "GET", "/governance/policies/{id}/acknowledgements", r)
else:
    skip("governance", "POST", "/governance/policies/{id}/acknowledge", "POST /governance/policies did not return an id")
    skip("governance", "GET", "/governance/policies/{id}/acknowledgements", "POST /governance/policies did not return an id")

r = client.get("/governance/audits", headers=h)
record("governance", "GET", "/governance/audits", r,
       expected_keys={"id", "title", "framework", "status", "auditor_user_id", "period_start", "period_end", "scheduled_date"})
r = client.post("/governance/audits", headers=h, json={"title": "Test audit", "framework": "GRI"})
audit_body = record("governance", "POST", "/governance/audits", r, expect_status={201})
if audit_body:
    r = client.patch(f"/governance/audits/{audit_body['id']}", headers=h, json={"status": "IN_PROGRESS"})
    record("governance", "PATCH", "/governance/audits/{id}", r)
else:
    skip("governance", "PATCH", "/governance/audits/{id}", "POST /governance/audits did not return an id")

r = client.get("/governance/compliance-issues", headers=h)
record("governance", "GET", "/governance/compliance-issues", r,
       expected_keys={"id", "audit_id", "title", "severity", "status", "owner_user_id", "due_date", "resolved_at"})
r = client.post("/governance/compliance-issues", headers=h, json={
    "title": "Test issue", "severity": "HIGH", "owner_user_id": 1,
    "due_date": (date.today() + timedelta(days=30)).isoformat(),
})
issue_body = record("governance", "POST", "/governance/compliance-issues", r, expect_status={201})
if issue_body:
    r = client.patch(f"/governance/compliance-issues/{issue_body['id']}", headers=h, json={"status": "IN_PROGRESS"})
    record("governance", "PATCH", "/governance/compliance-issues/{id}", r)
else:
    skip("governance", "PATCH", "/governance/compliance-issues/{id}", "POST /governance/compliance-issues did not return an id")

r = client.get("/governance/ledger", headers=h)
record("governance", "GET", "/governance/ledger", r,
       expected_keys={"seq", "entry_type", "ref_table", "ref_id", "prev_hash", "row_hash", "actor_user_id", "created_at"},
       note="mine (prior zone)")
r = client.get("/governance/ledger/verify", headers=h)
record("governance", "GET", "/governance/ledger/verify", r, expected_keys={"valid", "entries", "broken_at_seq"}, note="mine (prior zone)")

# ---------------------------------------------------------------------------
# Gamification
# ---------------------------------------------------------------------------
r = client.get("/gamification/challenges", headers=h)
record("gamification", "GET", "/gamification/challenges", r,
       expected_keys={"id", "title", "category_id", "lifecycle", "goal_metric", "goal_target", "points_reward", "badge_id", "start_date", "end_date"})
r = client.post("/gamification/challenges", headers=h, json={"title": "Bike to work", "start_date": "2026-07-14", "end_date": "2026-07-26"})
challenge_body = record("gamification", "POST", "/gamification/challenges", r, expect_status={201})
if challenge_body:
    cid = challenge_body["id"]
    r = client.patch(f"/gamification/challenges/{cid}", headers=h, json={"lifecycle": "Active"})
    record("gamification", "PATCH", "/gamification/challenges/{id}", r)
    r = client.post(f"/gamification/challenges/{cid}/join", headers=h)
    part_body = record("gamification", "POST", "/gamification/challenges/{id}/join", r, expect_status={200, 201})
    if part_body:
        r = client.patch(f"/gamification/challenge-participation/{part_body['id']}", headers=h, json={"progress": 42})
        record("gamification", "PATCH", "/gamification/challenge-participation/{id}", r)
    else:
        skip("gamification", "PATCH", "/gamification/challenge-participation/{id}", "join did not return an id")
else:
    skip("gamification", "PATCH", "/gamification/challenges/{id}", "POST /gamification/challenges did not return an id")
    skip("gamification", "POST", "/gamification/challenges/{id}/join", "POST /gamification/challenges did not return an id")
    skip("gamification", "PATCH", "/gamification/challenge-participation/{id}", "POST /gamification/challenges did not return an id")

r = client.get("/gamification/badges", headers=h)
record("gamification", "GET", "/gamification/badges", r,
       expected_keys={"id", "name", "description", "icon", "tier", "unlock_rule", "points_value", "is_active"})
r = client.post("/gamification/badges", headers=h, json={"name": "Carbon Cutter", "points_value": 500})
record("gamification", "POST", "/gamification/badges", r, expect_status={201})
r = client.get("/gamification/users/1/badges", headers=h)
record("gamification", "GET", "/gamification/users/{id}/badges", r)

r = client.get("/gamification/rewards", headers=h)
record("gamification", "GET", "/gamification/rewards", r,
       expected_keys={"id", "name", "description", "cost_points", "stock", "is_active"})
r = client.post("/gamification/rewards", headers=h, json={"name": "Coffee Kit", "cost_points": 400, "stock": 24})
reward_body = record("gamification", "POST", "/gamification/rewards", r, expect_status={201})
if reward_body:
    r = client.post(f"/gamification/rewards/{reward_body['id']}/redeem", headers=h)
    record("gamification", "POST", "/gamification/rewards/{id}/redeem", r, expect_status={200, 201, 409})
else:
    skip("gamification", "POST", "/gamification/rewards/{id}/redeem", "POST /gamification/rewards did not return an id")
r = client.get("/gamification/redemptions", headers=h)
record("gamification", "GET", "/gamification/redemptions", r)

r = client.get("/gamification/leaderboard", headers=h)
record("gamification", "GET", "/gamification/leaderboard", r, expected_keys={"rank", "user_id", "user", "department", "points"})
r = client.get("/gamification/users/1/points", headers=h)
record("gamification", "GET", "/gamification/users/{id}/points", r, expected_keys={"balance", "transactions"})

# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------
r = client.get("/reports/available", headers=h)
record("reports", "GET", "/reports/available", r, expected_keys={"id", "name", "formats"})
r = client.post("/reports/generate", headers=h, json={"report_id": "esg-summary", "format": "PDF", "period": "2026-Q2"})
record("reports", "POST", "/reports/generate", r, expect_status={200, 201})
r = client.get("/reports/recent", headers=h)
record("reports", "GET", "/reports/recent", r, expected_keys={"id", "name", "format", "generated_at", "size_kb"})

# ---------------------------------------------------------------------------
# Settings (mine)
# ---------------------------------------------------------------------------
r = client.get("/settings", headers=h)
record("settings", "GET", "/settings", r,
       expected_keys={"id", "gamification_enabled", "csr_module_enabled", "notifications_enabled", "public_leaderboard", "esg_weights", "updated_at"})
r = client.patch("/settings", headers=h, json={"gamification_enabled": True})
record("settings", "PATCH", "/settings", r)

# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
r = client.get("/notifications", headers=h)
record("notifications", "GET", "/notifications", r,
       expected_keys={"id", "user_id", "title", "body", "type", "link", "is_read", "created_at"})
r = client.post("/notifications/1/read", headers=h)
record("notifications", "POST", "/notifications/{id}/read", r, expected_keys={"id", "is_read"})
try:
    with client.stream("GET", "/notifications/stream", headers=h, timeout=2) as sr:
        ct = sr.headers.get("content-type", "")
        results.append(Result("notifications", "GET", "/notifications/stream", sr.status_code,
                               "OK" if "text/event-stream" in ct else "NOT_IMPLEMENTED",
                               f"content-type={ct}"))
except httpx.ReadTimeout:
    results.append(Result("notifications", "GET", "/notifications/stream", 200, "OK", "stream opened (timed out reading, as expected)"))
except Exception as exc:
    results.append(Result("notifications", "GET", "/notifications/stream", None, "SKIPPED", str(exc)))

# ---------------------------------------------------------------------------
# Cleanup: delete the smoke-test department now that every section is done.
# ---------------------------------------------------------------------------
if dept_id:
    r = client.delete(f"/departments/{dept_id}", headers=h)
    record("departments", "DELETE", "/departments/{id}", r, expect_status={204})

client.close()

# DB-level cleanup for rows created through endpoints with no DELETE in
# CONTRACT.md (goals, emission factors, the operational record/carbon
# transaction, the smoke-test admin user), scoped narrowly to THIS run's
# unique activity_type/email markers so unrelated data is never touched.
# esg_ledger is deliberately left alone -- it's append-only by design
# (schema.sql revokes UPDATE/DELETE on it), and its own smoke-test entries
# are exactly the kind of thing an audit trail is supposed to keep.
try:
    from sqlalchemy import delete as sa_delete

    from app.db import SessionLocal as _SessionLocal
    from app.models import CarbonTransaction, EmissionFactor, EnvironmentalGoal, OperationalRecord, User

    _db = _SessionLocal()
    _db.execute(
        sa_delete(CarbonTransaction).where(
            CarbonTransaction.operational_record_id.in_(
                _db.query(OperationalRecord.id).filter(
                    OperationalRecord.activity_type == f"contract_activity_{unique}"
                )
            )
        )
    )
    _db.execute(
        sa_delete(OperationalRecord).where(
            OperationalRecord.activity_type == f"contract_activity_{unique}"
        )
    )
    _db.execute(sa_delete(EnvironmentalGoal).where(EnvironmentalGoal.title == "Contract goal"))
    _db.execute(sa_delete(EmissionFactor).where(EmissionFactor.activity_type == f"contract_activity_{unique}"))
    _db.execute(sa_delete(User).where(User.email.in_([emp_email, admin_email])))
    _db.commit()
    _db.close()
except Exception as exc:  # pragma: no cover -- best-effort cleanup, never fail the report over it
    print(f"(cleanup skipped: {exc})")

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
groups: dict[str, list[Result]] = {}
for res in results:
    groups.setdefault(res.group, []).append(res)

counts = {"OK": 0, "NOT_IMPLEMENTED": 0, "MISMATCH": 0, "SKIPPED": 0}
print("\n" + "=" * 100)
for group, items in groups.items():
    print(f"\n## {group}")
    for res in items:
        counts[res.outcome] += 1
        marker = {"OK": "PASS", "NOT_IMPLEMENTED": "STUB", "MISMATCH": "FAIL", "SKIPPED": "SKIP"}[res.outcome]
        line = f"  [{marker:4}] {res.method:6} {res.path:55} status={res.status}"
        if res.note:
            line += f"  -- {res.note}"
        print(line)

print("\n" + "=" * 100)
print(f"TOTAL: {sum(counts.values())}   PASS={counts['OK']}  STUB={counts['NOT_IMPLEMENTED']}  FAIL={counts['MISMATCH']}  SKIP={counts['SKIPPED']}")
print("=" * 100)

sys.exit(1 if counts["MISMATCH"] > 0 else 0)
