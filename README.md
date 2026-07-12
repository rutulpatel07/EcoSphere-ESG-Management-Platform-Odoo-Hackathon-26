# EcoSphere ESG Management Platform — Architecture & Internals

**Owner zone only.** This document covers the system problem, architecture, and operational model.

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
│  Frontend (React)                                         │
│  ├─ Dashboard (ESG summary, KPIs, trends)                │
│  ├─ Environmental (goals, emission records, factors)      │
│  ├─ Social (CSR activities, participation, challenges)    │
│  ├─ Governance (policies, audits, compliance, ledger)     │
│  └─ Gamification (badges, rewards, leaderboard)          │
│                                                            │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  Backend API (FastAPI)                                    │
│  ├─ Auth Router (JWT login, token validation)             │
│  ├─ Environmental Router                                  │
│  ├─ Social Router                                         │
│  ├─ Governance Router (+ ledger verification)             │
│  ├─ Gamification Router                                   │
│  └─ Dashboard Router (aggregation & scoring)              │
│                                                            │
├──────────────────────────────────────────────────────────┤
│                                                            │
│  Database (PostgreSQL + TimescaleDB)                      │
│  ├─ Core tables (users, departments, settings)            │
│  ├─ Environmental schema                                  │
│  │  ├─ emission_factors (versioned, valid_from/to)        │
│  │  ├─ operational_records (activity captures)            │
│  │  └─ carbon_transactions (factor snapshot + result)      │
│  ├─ Social schema (categories, activities, participation) │
│  ├─ Governance schema                                     │
│  │  ├─ policies, policy_acknowledgements                  │
│  │  ├─ audits, compliance_issues                          │
│  │  └─ esg_ledger (immutable, hash-chained)               │
│  └─ Gamification schema (badges, challenges, rewards)      │
│                                                            │
└──────────────────────────────────────────────────────────┘
```

## Three Differentiators

### 1. Hash-Chained Ledger
Every material change (policy acknowledgement, compliance issue resolution, etc.) is recorded in `esg_ledger`:
- **seq**: Monotonic sequence number
- **prev_hash**: SHA-256 hash of previous entry
- **row_hash**: SHA-256 of current entry data
- **actor_user_id & created_at**: Immutable timestamp and who made the change

The chain is cryptographically linked: to fake an entry, you must recompute all subsequent hashes. The `/governance/ledger/verify` endpoint detects any break in the chain and reports the first corrupted sequence number.

**Use case**: Regulatory audits. Prove no compromise of governance history.

### 2. Live Closed Loop
When an `operational_record` is posted (e.g., 1800L of diesel fleet usage):
- **That moment**, the system snapshots the active emission factor for `diesel_fleet`
- Creates a `carbon_transaction` recording:
  - `factor_value_used` (e.g., 2.6871 kgCO2e/L)
  - `factor_version_used` (e.g., version 2)
  - `co2e_kg` result (quantity × factor)
  - `uncertainty_pct` from that factor version

The transaction is **sealed at measurement time**, not locked later. Science can update; this record never changes.

**Use case**: Month-end reports are reproducible. Changing a factor in December doesn't alter June's baseline.

### 3. Factor-Version Recompute
When a new emission factor version is published (e.g., DEFRA 2025 electricity data):
- Old transactions keep their locked `factor_version_used`
- New records use the new version
- Recompute aggregates (ESG score, departmental totals) across transactions with different factor versions

The system does NOT retroactively "fix" old emissions. Instead:
- **Calculated** records can be flagged for re-measurement (to use new factor)
- **Measured** records are immutable (gold standard)
- Historical data traces show which factor version was used, explaining any score drift

**Use case**: Science evolves (grids decarbonize). Scores reflect both old and new data honestly.

## Schema Overview

### Core Entities
| Table | Purpose |
|-------|---------|
| `users` | ID, email, role (ADMIN/MANAGER/EMPLOYEE), department, points balance |
| `departments` | Org hierarchy (parent_id), manager assignment |
| `settings` | Global config (gamification on/off, ESG weights E/S/G) |

### Environmental
| Table | Purpose |
|-------|---------|
| `emission_factors` | Versioned factors (activity_type, version, valid_from/to, uncertainty) |
| `operational_records` | Activities (op_type, qty, unit, occurred_on, creates carbon_transaction) |
| `carbon_transactions` | Sealed result (qty × factor_value @ factor_version, scope, data_tier) |
| `environmental_goals` | Baseline → target (metric, dates, status) |
| `products` | ESG profiles (embodied carbon, water, certifications) |

### Social
| Table | Purpose |
|-------|---------|
| `social_categories` | CSR or CHALLENGE |
| `csr_activities` | Volunteer events (capacity, points reward, proof_url) |
| `csr_participation` | User joins activity (unique on activity_id + user_id) |

### Governance
| Table | Purpose |
|-------|---------|
| `policies` | Mandatory policies (version, effective_date) |
| `policy_acknowledgements` | User acks (unique on policy_id + user_id, created → ledger entry) |
| `audits` | GRI / ISO scope / date range |
| `compliance_issues` | Risks raised during audits (severity, due_date, resolution status) |
| `esg_ledger` | **Hash-chained immutable log** (seq, prev_hash, row_hash, ref_table, ref_id) |

### Gamification
| Table | Purpose |
|-------|---------|
| `badges` | Unlockable achievement (unlock_rule, tier, points_value) |
| `challenges` | Goal-based competition (metric, target, lifecycle) |
| `challenge_participation` | User progress (unique on challenge_id + user_id) |
| `rewards` | Redeemable prizes (cost_points, stock) |
| `point_transactions` | Audit trail (reason, balance delta, created_at) |

## Setup Steps

### Development
1. **Clone repo**
   ```bash
   cd /path/to/repo
   ```

2. **Backend dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Database initialization**
   ```bash
   # Create PostgreSQL database
   psql -U postgres -c "CREATE DATABASE ecosphere_dev;"
   
   # Run Alembic migrations
   alembic upgrade head
   
   # Seed data (optional)
   psql -U postgres -d ecosphere_dev -f scripts/seed.sql
   ```

4. **Frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

5. **Run services**
   - Backend: `python -m uvicorn main:app --reload --port 8000`
   - Frontend: `npm start` (default :3000)
   - Database: via Docker or local postgres

### Production
- Use `docker-compose.yml` (postgres service + backend container)
- Set `DATABASE_URL`, `JWT_SECRET` env vars
- TimescaleDB extension recommended for time-series data (carbon transactions with occurred_on)

## Scaling Path

**Current**: Single FastAPI instance, PostgreSQL (no sharding).

**Next (100k+ records/day)**:
- **TimescaleDB**: Enable hypertables on `carbon_transactions` (partition by time)
- **Queue workers** (named, not installed): Async emission factor snapshot service
  - POST to `/environmental/operational-records` → enqueue to worker
  - Worker snaps factor version, inserts carbon_transaction, returns ID
  - Frontend polls or webhooks for result
- **Read replicas**: Report generation against replica
- **Materialized views**: Pre-aggregate ESG scores by department/date

**Future**:
- Batch factor recompute job (nightly)
- Ledger archival (cold storage for entries > 2 years)

## Team Roles & Permissions

| Role | Capabilities |
|------|--------------|
| **ADMIN** | Full access; create policies, audits, factors; acknowledge all notifications |
| **MANAGER** | View dept totals; approve CSR participation; manage team challenges |
| **EMPLOYEE** | Log activities, join CSR/challenges, view personal points & badges |

**Ledger access**: Any authenticated user can read `/governance/ledger`; verify is read-only.

**Factor creation**: ADMIN only.

---

**Last updated**: 2026-07-12
