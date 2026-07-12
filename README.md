# EcoSphere ESG Management Platform

A real-time, tamper-evident ESG (Environmental, Social, Governance) reporting platform. FastAPI + PostgreSQL backend, React + Vite frontend.

## Quick Start (local testing)

Two things must be running: **PostgreSQL** (with the schema applied + seeded), the **backend** (port 8000), and the **frontend** (port 5173). Commands below use Git Bash / macOS / Linux shell syntax; PowerShell equivalents are noted where they differ.

### 1. Database

```bash
# Create the role + database (skip if they already exist)
psql -U postgres -c "CREATE ROLE ecosphere WITH LOGIN PASSWORD 'ecosphere';"
psql -U postgres -c "CREATE DATABASE ecosphere_db OWNER ecosphere;"

# Apply the schema (tables, enums, the esg_ledger append-only trigger)
psql -U ecosphere -d ecosphere_db -f backend/db/schema.sql
```

Already have an older `ecosphere_db` running and don't want to wipe it? Apply the incremental migrations instead of re-running `schema.sql`:
```bash
psql -U ecosphere -d ecosphere_db -f backend/db/migrations/002_ledger_trigger.sql
psql -U ecosphere -d ecosphere_db -f backend/db/migrations/003_settings_feature_flags.sql
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set JWT_SECRET — there is no default, the app refuses to start without it.
# Generate one with: python -c "import secrets; print(secrets.token_urlsafe(32))"

python -m seed                # loads the demo dataset (Bharti Industries, 25 users)
python -m uvicorn app.main:app --reload --port 8000
```

> **Windows note:** if `python -m seed` throws a `UnicodeEncodeError` on the ✓/✅ characters (default `cp1252` console), run it as:
> `PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python -m seed`

Backend is up when `curl http://localhost:8000/health` returns `{"status":"ok",...}`. API docs: `http://localhost:8000/docs`.

### 3. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. `frontend/.env` (`VITE_API_BASE=http://localhost:8000/api`) already points at the backend above — only edit it if the backend runs somewhere else.

### 4. Log in

Every seeded user shares the password **`bharti@123`**:

| Email | Role | Department |
|---|---|---|
| `ceo@bharti.in` | ADMIN | Corporate Affairs |
| `cfo@bharti.in` | MANAGER | Corporate Affairs |
| `mfg_head@bharti.in` | MANAGER | Manufacturing |
| `mfg_eng1@bharti.in` | EMPLOYEE | Manufacturing |

(22 more seeded users across Manufacturing, Logistics, R&D, Sales, and Corporate — see `backend/seed.py` for the full roster.) `/signup` also works and always creates a fresh EMPLOYEE account.

### 5. Smoke-test the closed loop

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ceo@bharti.in","password":"bharti@123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://localhost:8000/api/environmental/operational-records \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"op_type":"MANUFACTURING","activity_type":"Electricity","quantity":1000,"unit":"kWh","occurred_on":"2026-07-12"}'

curl -s http://localhost:8000/api/governance/ledger/verify -H "Authorization: Bearer $TOKEN"
# -> {"valid": true, "entries": N, "broken_at_seq": null}
```

Or just do it in the browser: log in as the admin above, go to **Environmental → Carbon Transactions**, use the **Log Operation** form, and watch the Dashboard's ESG score and Recent Activity feed update live (SSE) without a page refresh.

---

## The Problem

Organizations need a **tamper-proof, real-time ESG reporting system** that:
- Captures emissions and social impact as activities occur (not retroactively)
- Locks factor versions at measurement time (not recomputation time)
- Detects any historical tampering via cryptographic proof
- Recomputes impact when science updates, without losing audit trail

Existing systems either compromise on real-time accuracy or audit immutability.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                   EcoSphere Platform                      │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  Frontend (React + Vite, SSE-driven live updates)         │
│  ├─ Dashboard (ESG summary, KPIs, trends, live ledger)    │
│  ├─ Environmental (goals, log operation, factors, recompute)│
│  ├─ Social (CSR activities, participation, challenges)    │
│  ├─ Governance (policies, audits, compliance, ledger)      │
│  ├─ Gamification (badges, rewards, leaderboard)           │
│  └─ Reports (canned + custom cross-module exports)        │
│                                                            │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  Backend API (FastAPI)                                    │
│  ├─ Auth Router (JWT login/signup, role-guarded routes)   │
│  ├─ Environmental / Operations / Carbon Routers            │
│  ├─ Social / CSR Routers                                  │
│  ├─ Governance Router (+ ledger read/verify)               │
│  ├─ Gamification / Challenges Routers                     │
│  ├─ Reports, Settings, Notifications Routers               │
│  └─ Dashboard Router (aggregation & scoring)               │
│                                                            │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  Database (PostgreSQL)                                     │
│  ├─ Core tables (users, departments, settings)             │
│  ├─ Environmental schema                                   │
│  │  ├─ emission_factors (versioned, valid_from/to)         │
│  │  ├─ operational_records (activity captures)             │
│  │  └─ carbon_transactions (factor snapshot + result)      │
│  ├─ Social schema (categories, csr_activities, employee_participation) │
│  ├─ Governance schema                                      │
│  │  ├─ esg_policies, policy_acknowledgements                │
│  │  ├─ audits, compliance_issues                            │
│  │  └─ esg_ledger (append-only, hash-chained, DB-trigger-enforced) │
│  └─ Gamification schema (badges, challenges, rewards, point_transactions) │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

## Three Differentiators

### 1. Hash-Chained, Append-Only Ledger
Every material change — carbon transactions, point awards, badge unlocks, policy acknowledgements, compliance issue create/status-change — is recorded in `esg_ledger`:
- **seq**: Monotonic sequence number
- **prev_hash**: SHA-256 hash of the previous entry
- **row_hash**: `SHA256(prev_hash + canonical_json({entry_type, ref_table, ref_id, actor_user_id, payload}))` — provenance columns are folded into the hash, not just the payload
- **actor_user_id & created_at**: who made the change, and when

The chain is cryptographically linked: tampering with any row (payload *or* metadata) breaks every hash after it. `GET /governance/ledger/verify` walks the chain and reports the first broken `seq`. A `BEFORE UPDATE OR DELETE` Postgres trigger makes the table append-only at the database level (not just via a `REVOKE`, which the table owner can bypass) — see `backend/db/migrations/002_ledger_trigger.sql`.

**Use case**: Regulatory audits. Prove no compromise of governance history.

### 2. Live Closed Loop
When an `operational_record` is posted (e.g., 1000 kWh of electricity):
- **That moment**, the system snapshots the active emission factor
- Creates a `carbon_transaction` recording `factor_value_used`, `factor_version_used`, `co2e_kg`, and `uncertainty_pct`, all in the same DB transaction as a `CARBON` ledger entry
- The department's E/S/G score is refreshed in the same transaction, and an SSE event (`carbon.created`, `score.updated`) is published after commit

The frontend subscribes to `GET /environmental/events` (SSE) and refetches the dashboard on either event — the score and Recent Activity feed move live, with no manual refresh.

**Use case**: Month-end reports are reproducible. Changing a factor in December doesn't alter June's baseline.

### 3. Factor-Version Recompute
`POST /environmental/carbon-transactions/recompute?factor_version=N` re-prices every carbon transaction against a target factor version while holding quantities constant, splitting the total movement into:
- **Methodology change**: the factor value changed
- **Real change**: always 0 for a pure recompute (activity data didn't move) — reported explicitly rather than hidden, so the number is honest about what it represents

Old transactions keep their locked `factor_version_used`; recompute is a read-only "what-if", not a retroactive rewrite.

**Use case**: Science evolves (grids decarbonize). Scores reflect both old and new data honestly.

## Schema Overview

### Core Entities
| Table | Purpose |
|-------|---------|
| `users` | Email, bcrypt hash, role (ADMIN/MANAGER/EMPLOYEE), department, `is_active` |
| `departments` | Org hierarchy (`parent_id`), manager assignment |
| `settings` | Singleton row (id=1): module toggles, `esg_weights`, `evidence_required`, `auto_award_badges`, `auto_emission_calc` |

### Environmental
| Table | Purpose |
|-------|---------|
| `emission_factors` | Versioned, append-only factors (`activity_type`, `version`, `valid_from/to`, `uncertainty_pct`) |
| `operational_records` | Raw activity capture (`op_type`, `quantity`, `unit`, `occurred_on`) |
| `carbon_transactions` | Sealed result: quantity × factor snapshot, `scope`, `data_tier` |
| `environmental_goals` | Baseline → target tracking |
| `product_esg_profiles` | Product-level embodied carbon, water use, certifications |

### Social
| Table | Purpose |
|-------|---------|
| `categories` | CSR or CHALLENGE type, shared with Gamification |
| `csr_activities` | Volunteer events (capacity, `points_reward`) |
| `employee_participation` | User ↔ activity join (unique per pair), verification workflow |

### Governance
| Table | Purpose |
|-------|---------|
| `esg_policies` | Mandatory/optional policies (`version`, `effective_date`) |
| `policy_acknowledgements` | User acks (unique per policy+user), each one ledgered |
| `audits` | Framework/scope/date-range audit records |
| `compliance_issues` | Risks raised (severity, `due_date`, resolution status), create + status-change ledgered |
| `esg_ledger` | Hash-chained, append-only log (`seq`, `prev_hash`, `row_hash`, `ref_table`, `ref_id`, `payload`) |

### Gamification
| Table | Purpose |
|-------|---------|
| `badges` | Unlock rule (JSONB), tier, `points_value`; unlocks are ledgered |
| `challenges` / `challenge_participation` | Goal-based competitions, lifecycle-gated |
| `rewards` / `reward_redemptions` | Redeemable prizes; redemption is a single locked transaction (`pg_advisory_xact_lock` per user, prevents double-spend) |
| `point_transactions` | Single source of truth for balances (`SUM(points)`) — `users.points_balance` is deprecated and unused |

## Development Setup (detailed)

Steps 1–3 mirror the [Quick Start](#quick-start-local-testing) above with more explanation.

1. **Database** — PostgreSQL 16+, extension `pgcrypto`. Either run it natively (commands above) or via Docker (`docker compose up -d db`, see `docker-compose.yml` — note the Docker Postgres uses database name `ecosphere`, not `ecosphere_db`; keep `DATABASE_URL` consistent with whichever path you pick).

2. **Backend** — Python 3.11+. `backend/.env` (git-ignored) holds `DATABASE_URL` and `JWT_SECRET`; `backend/.env.example` is the committed template. Config is loaded via `python-dotenv` at import time (`app/config.py`) — a missing `JWT_SECRET` raises immediately rather than falling back to an insecure default. `requirements.txt` versions are pinned to what's actually been tested.

3. **Frontend** — Node 18+. `frontend/.env` / `.env.example` hold `VITE_API_BASE`. Dev server is Vite (`npm run dev`, port 5173); `npm run build` type-checks (`tsc`) then builds.

4. **Tests** — `cd backend && python -m unittest discover tests` (or `pytest`). Covers the ledger hash chain and the scoring formulas; no DB required for these.

### Production
- `docker-compose.yml` builds the backend container and a Postgres service; set `DATABASE_URL` and a real `JWT_SECRET` via environment, not the file defaults.
- Set `CORS_ORIGINS` to the deployed frontend origin.
- TimescaleDB is a scaling option (see below), not currently wired in.

## Scaling Path

**Current**: Single FastAPI instance, PostgreSQL (no sharding), APScheduler for background jobs (overdue compliance issues + unacknowledged mandatory policies, hourly).

**Next (100k+ records/day)**:
- **TimescaleDB**: Enable hypertables on `carbon_transactions` (partition by time)
- **Queue workers**: Async emission factor snapshot service instead of inline commit
- **Read replicas**: Report generation against a replica
- **Materialized views**: Pre-aggregate ESG scores by department/date

**Future**:
- Batch factor recompute job (nightly)
- Ledger archival (cold storage for entries older than the retention window)

## Roles & Permissions

Enforced server-side on every route via `core/deps.py` (`get_current_user` requires an active user; `require_manager` = ADMIN or MANAGER; `require_admin` = ADMIN only). The frontend mirrors these so the UI never shows a control that would 403.

| Role | Capabilities |
|------|--------------|
| **ADMIN** | Everything MANAGER can do, plus `PATCH /settings` (module toggles, ESG weights, evidence/auto-award/auto-emission-calc flags) and user promotion |
| **MANAGER** | Create/edit policies, audits, compliance issues, badges, rewards, categories, challenges, CSR activities; verify/approve CSR & challenge participation (**cannot approve their own** — self-approval is rejected even for managers) |
| **EMPLOYEE** | Log operational records, join CSR activities/challenges, redeem rewards, view own points/badges, acknowledge policies, read everything else |

Reads are authenticated-only across the board. `GET /gamification/users/{id}/points` and `/badges` are restricted to the user themselves or a manager/admin. Signup (`POST /auth/signup`) always creates an EMPLOYEE — role is never client-controlled at account creation.

---

**Last updated**: 2026-07-12
