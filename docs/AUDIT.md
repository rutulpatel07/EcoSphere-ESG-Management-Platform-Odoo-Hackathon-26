# EcoSphere — Brutal Codebase Audit

**Scope:** FastAPI backend (`backend/`) + React/Vite frontend (`frontend/`) + PostgreSQL schema (`backend/db/schema.sql`).
**Method:** Read the actual code, not the plan. Read-only. No files changed except this report.
**Reviewer stance:** External hiring panel grading database design, security, and correctness hardest. Findings are not softened.

**Headline:** The backend is genuinely good — the atomic closed-loop write, the Decimal carbon math, and the hash-chain logic are real and mostly correct. But the two things a panel will actually poke — **RBAC** and the **live differentiator in the browser** — are broken. The flagship "live closed loop" cannot be demonstrated through the UI (SSE route mismatch + no log-emission form), and eight write-heavy endpoints have **no role enforcement at all**, letting any employee approve their own rewards and edit governance records. The JWT secret the app actually runs on is the committed placeholder.

---

## 1. System map

What's actually built: a FastAPI monolith (`app/main.py` mounts 16 routers under `/api`) over a 25-table Postgres schema applied from a single authoritative `schema.sql`. Two parallel carbon/scoring engines exist in `app/services/` (emissions, ledger, scoring, events) and a second cluster of feature services in `app/services_features/` (points, badges, rewards, evidence, notifications, reports). Posting an operational record atomically creates a snapshotted `carbon_transaction`, appends a hash-chained `esg_ledger` row, refreshes the department's ESG score, and (server-side) publishes SSE — all in one transaction. Gamification (points summed from a ledger table, auto-awarded badges, stock-checked reward redemption), governance (policies/audits/compliance issues with a legal-transition state machine + an hourly overdue sweep), and a 4-generator + custom report builder with CSV/XLSX/PDF export are all implemented. The React frontend is 7 screens wired mostly to live data via a thin `useApi` hook, with a handful of mock fallbacks and one **fatally mismatched SSE route**. Auth is split across **two independent JWT dependencies** with very different guarantees — the root cause of the RBAC findings below.

### API endpoint map

Legend: **Auth** = `A` core.deps role-aware / `a` auth_dep authn-only / `—` open. **FE?** = does the frontend actually call it.

| Endpoint | File | Auth | FE? |
|---|---|---|---|
| `POST /auth/signup` | routers/auth.py | — | ❌ (FE signup is **mock-only** — see §6) |
| `POST /auth/login` | routers/auth.py | — | ✅ AuthApi.login |
| `GET /auth/me` | routers/auth.py | A | ❌ |
| `POST /auth/promote/{id}` | routers/auth.py | A admin | ❌ |
| `GET /departments` · `GET /{id}` | routers/departments.py | A | ✅ (list) |
| `POST /departments` · `PATCH` · `DELETE /{id}` | routers/departments.py | A admin | ❌ |
| `GET /dashboard/summary` | routers/dashboard.py | a | ✅ DashboardApi.summary |
| `GET /environmental/goals` | routers/environmental.py | A | ✅ |
| `POST /environmental/goals` · `PATCH /{id}` | routers/environmental.py | A manager | ❌ |
| `GET /environmental/emission-factors` | routers/environmental.py | A | ✅ |
| `POST /environmental/emission-factors` | routers/environmental.py | A manager | ❌ |
| `GET /environmental/products` | routers/environmental.py | A | ✅ |
| `POST /environmental/products` | routers/environmental.py | A manager | ❌ |
| `GET /environmental/scores` · `/scores/org` · `POST /scores/refresh` | routers/environmental.py | A(mgr on refresh) | ❌ |
| `POST /environmental/operational-records` | routers/operations.py | A | ❌ **(no UI — closed-loop trigger not exposed)** |
| `GET /environmental/operational-records` | routers/operations.py | A | ❌ |
| `GET /environmental/carbon-transactions` | routers/carbon.py | A | ✅ |
| `POST /environmental/carbon-transactions/recompute` | routers/carbon.py | A manager | ❌ (no UI) |
| `GET /environmental/events` (SSE) | routers/carbon.py | — | ❌ **(FE listens to `/notifications/stream` instead — see §7)** |
| `GET/POST /social/categories` | routers/social.py | a | ✅ (get) |
| `GET/POST/PATCH /social/activities…` | routers/csr.py | a | ✅ (list) |
| `GET /social/activities/{id}/participants` | routers/csr.py | a | ✅ |
| `POST /social/activities/{id}/join` | routers/csr.py | a | ✅ |
| `PATCH /social/participation/{id}` | routers/csr.py | a | ✅ (verify/approve) |
| `GET/POST/PATCH /governance/policies…` | routers/governance.py | a | ✅ (list) |
| `POST /governance/policies/{id}/acknowledge` | routers/governance.py | a | ❌ |
| `GET/POST/PATCH /governance/audits…` | routers/governance.py | a | ✅ (list) |
| `GET/POST/PATCH /governance/compliance-issues…` | routers/governance.py | a | ✅ (list) |
| `GET /governance/ledger` · `/ledger/verify` | routers/ledger.py | A | ✅ |
| `GET/POST /gamification/badges` · `GET /users/{id}/badges` | routers/gamification.py | a | ✅ |
| `GET/POST /gamification/rewards` | routers/gamification.py | a | ✅ (list) |
| `POST /gamification/rewards/{id}/redeem` | routers/gamification.py | a | ✅ |
| `GET /gamification/redemptions` · `GET /users/{id}/points` | routers/gamification.py | a | ❌ |
| `GET /gamification/leaderboard` | routers/gamification.py | a | ✅ |
| `GET/POST/PATCH /gamification/challenges…` | routers/challenges.py | a | ✅ (list) |
| `POST /gamification/challenges/{id}/join` | routers/challenges.py | a | ✅ |
| `PATCH /gamification/challenge-participation/{id}` | routers/challenges.py | a | ❌ |
| `GET /reports/available` · `/recent` · `POST /generate` | routers/reports.py | a | ✅ |
| `POST /reports/custom` | routers/reports.py | a | ❌ (custom builder not wired) |
| `GET/PATCH /settings` | routers/settings.py | A(admin on patch) | ✅ |
| `GET /notifications` · `POST /{id}/read` | routers/notifications.py | a | ✅ |
| `GET /users/ping` | routers/users.py | — | ❌ **(users module is a stub — no user CRUD)** |
| `GET /notifications/stream` | — | — | ✅ **called by FE but DOES NOT EXIST** |

---

## 2. Spec-compliance check

### Section 4 — Data model
All required tables present (25 modelled, matching `schema.sql`; ORM in `app/models/`). ✅

- 22 mandated tables + `categories`, `product_esg_profiles`, `department_scores` extras — all present. ✅
- `compliance_issues.owner_user_id NOT NULL` + `due_date NOT NULL` — ✅ `schema.sql:441-442` (owner is `ON DELETE RESTRICT`, correct).
- Unique constraints — ✅ `emission_factors(activity_type,version)`, `employee_participation(activity,user)`, `challenge_participation(challenge,user)`, `user_badges(user,badge)`, `department_scores(dept,period)`, `policy_acknowledgements(policy,user)`, `settings` singleton `CHECK(id=1)`, `rewards CHECK(stock>=0)`, `users.email UNIQUE`. Well done — this is the strongest part of the submission.
- ⚠ `users.password_hash VARCHAR(72)` — bcrypt hashes are 60 chars so fine, but a 72-cap is a footgun if the algo ever changes.

### Section 5 — Business workflow (masters → ops → carbon → scores → dashboard)
Chain intact **server-side**: ✅ `operations.py:79` → `emissions.record_operation` → `scoring.refresh_department_score` → `dashboard.summary`. ⚠ **Ops-entry step is not exposed in the UI** — there is no frontend form that POSTs `/environmental/operational-records`, so the chain cannot be driven end-to-end from the browser (see §6/§7).

### Section 8 — The six rules
1. **Auto emission calc** — ✅ `emissions.record_operation` (`emissions.py:75`). ⚠ The `.env` `AUTO_EMISSION_CALC` toggle is never read — calc is unconditional. Cosmetic.
2. **Evidence gate** — ✅ `csr.py:222` and `challenges.py:209` block verify/complete unless `proof_url` set. Note it's a hardcoded constant `EVIDENCE_REQUIRED` (`services_features/evidence.py`), not a settings column.
3. **Badge auto-award** — ✅ `badges.evaluate_badges` runs after every point delta (`points.py:52`). Hardcoded `AUTO_AWARD_BADGES=True`.
4. **Reward redemption w/ stock** — ✅ `rewards.redeem` with `SELECT … FOR UPDATE` + stock/balance checks. ⚠ user-balance race (see §4).
5. **Notifications 4 types** — ⚠ **partial**. Constants for COMPLIANCE/APPROVAL/POLICY/BADGE exist (`notifications_service.py`), and COMPLIANCE (`governance.py:342` + `scheduler.py`), APPROVAL (`csr.py`/`challenges.py`), BADGE (`badges.py`) are actually emitted. **POLICY is defined but never raised anywhere** — no code path produces a POLICY notification. 3 of 4 wired.
6. **Compliance overdue flagging** — ✅ `scheduler.py` hourly idempotent sweep. ⚠ ignores `settings.notifications_enabled`.

### Section 7 — Reports
- 4 generators — ✅ `reports_data.py` env/social/gov/esg.
- Custom builder — ✅ `custom_report` (6 filters, UNION across modules). ⚠ **not wired to the UI**; the Reports page's framework/scope/data-tier controls are cosmetic and `POST /reports/custom` is never called.
- 3 exports — ✅ CSV/XLSX/PDF (`exporters.py`), all local libs.

---

## 3. Differentiator integrity

### (a) Hash-chained ledger — ⚠ works but the immutability claim is overstated
- `row_hash = SHA256(prev_hash + canonical_json(payload))` — ✅ **correct and deterministic** (`ledger.py:47`). Canonical JSON (sorted keys, numbers-as-strings) survives the JSONB round-trip; genesis `prev_hash=None→""`; a Postgres advisory xact lock serializes concurrent appends so the chain can't fork. `/ledger/verify` genuinely re-walks and re-derives every row (`ledger.py:130` → `verify_chain`). This part is real.
- ❌ **The hash covers only `prev_hash + payload`.** It excludes `entry_type`, `ref_table`, `ref_id`, `actor_user_id`, `seq`, `created_at`. The schema comment claims "sha256 over (seq, prev_hash, payload, …)" — **the code doesn't match the comment**. Anyone who can mutate the table can rewrite the actor, ref, or entry_type of any row and `/ledger/verify` still returns `valid: true`.
- ❌ **"UPDATE/DELETE revoked" is not actually enforced.** `REVOKE UPDATE, DELETE ON esg_ledger FROM PUBLIC` (`schema.sql:257`) does **not** bind the table owner or a superuser, and the app connects as `ecosphere`, which owns the schema. There is no `BEFORE UPDATE/DELETE` trigger. So for the role the app actually uses, the ledger is fully mutable. A DB-savvy judge will call this out.
- ❌ **Scope gap:** only `entry_type='CARBON'` rows are ever appended (`emissions.py:138`). Points, badges, policy acks, and governance changes are **not** ledgered, despite `entry_type` advertising POINTS/POLICY/AUDIT. The "tamper-evident audit trail" covers carbon only.

### (b) Live closed loop — ✅ server-side, ❌ end-to-end in the browser
- Server-side is **correct and atomic**: `operations.create_operational_record` stages record + carbon txn + ledger entry, refreshes the score in the **same transaction** (`publish=False`), commits once, then emits `carbon.created` + `score.updated` **after** commit (`operations.py:78-118`). Textbook. Rollback on any failure. This is genuinely well done.
- ❌ **The SSE never reaches the UI.** Backend publishes to `GET /environmental/events` (`carbon.py:124`). The frontend's `useNotificationsStream` connects to `GET /notifications/stream` (`useNotificationsStream.ts:16`) — **a route that does not exist** (explicitly stubbed out in `notifications.py:11`). Nothing in the frontend ever subscribes to `/environmental/events`. Result: the Dashboard "live updates" badge is permanently ⚪ unavailable, and no screen live-updates.
- ❌ **No trigger in the UI.** There is no frontend form to POST an operational record, so even if SSE were wired, there's nothing to fire it from the browser. The flagship differentiator is **API-only** and cannot be shown live on stage.

### (c) Factor-version recompute — ✅ correct, ❌ no UI
- `recompute` (`carbon.py:52`) re-prices every txn against a target version, splits `methodology_change` (factor value moved) vs `real_change` (activity moved). Because quantities are held constant, `real_change = total_delta − methodology = 0` **by construction**, and it's reported honestly with a `note` explaining why. Correct and auditable. Not wired to any UI (no recompute button); demoable via API only.

---

## 4. Correctness & data-integrity risks

- **Reward redemption user-balance race — Med.** `rewards.redeem` locks the **reward** row `FOR UPDATE` (`rewards.py:21`), which protects stock, but the balance is `SUM(point_transactions)` (`points.py:16`) and **the user is never locked**. Two concurrent redemptions of *different* rewards by the same user each read the same balance and can both pass the check → the user overspends and goes negative. Lock the user (or an advisory lock keyed by `user_id`), or re-check balance under a user-scoped lock.
- **Dual source of truth for points — Med.** Balances are correctly derived from `point_transactions` everywhere in the app, but `users.points_balance` still exists and `seed.py:912` writes it. It will silently diverge from reality and mislead anyone who queries it. Drop the column or stop writing it.
- **Score staleness after gamification — Med.** Awarding CSR/challenge points does **not** refresh `department_scores`. Only operational-record writes, goal/factor edits, and settings changes trigger a refresh (`operations.py`, `environmental.py`, `settings.py`). So verifying a CSR activity moves nobody's Social score on the dashboard until an unrelated carbon event or a manual `/scores/refresh`. The "live" story is inconsistent across modules.
- **co2e math — ✅ clean.** `Decimal` throughout with `quantize(1e-6)` (`emissions.py:26,102`); the exact stored value is what's hashed into the ledger. No float in the money/carbon path. Scoring uses `float()` but only for 0–100 outputs rounded to 2dp — acceptable.
- **Transaction boundaries — mostly ✅.** `award_points → evaluate_badges → create_notification` all run in the same Session and commit once (`csr.py`, `challenges.py`) — no desync there. The one real desync risk is (a) above: a domain write and its ledger append are atomic *for carbon*, but non-carbon domain writes have no ledger append at all.
- **`get_current_user_id` doesn't check the user exists/active — Med.** (`auth_dep.py:17`) A token minted for a since-deleted or deactivated user still authorizes on every `a`-guarded route. `core.deps.get_current_user` does check (`deps.py:47`); the two auth paths disagree.
- **Recompute reads the whole table into memory** (`carbon.py:58 select(CarbonTransaction)`) — fine for a demo, O(n) memory at scale. Low.

---

## 5. Security audit

**HIGH**
- **RBAC is not enforced on ~8 write surfaces.** Every router wired to `services_features/auth_dep.get_current_user_id` checks *authentication only, never role*: csr, challenges, gamification, governance, social, dashboard, reports, notifications. Concretely, **any EMPLOYEE can:**
  - `PATCH /social/participation/{id}` → set status `VERIFIED` on **their own** participation and trigger `award_points` to themselves (`csr.py:207-262`). Self-approval + points farming.
  - `PATCH /gamification/challenge-participation/{id}` → mark their own participation `COMPLETED` and self-award XP (`challenges.py:195-250`).
  - Create/patch **ESG policies, audits, and compliance issues** (`governance.py`) — governance record integrity is wide open.
  - Create badges, rewards, categories, challenges, CSR activities.

  The role machinery exists (`core.deps.require_manager/require_admin`) and is correctly used by the environmental/carbon/departments/settings/auth routers — it simply wasn't applied to the second half of the app. This is the single most damaging finding for a panel.
- **The app runs on the committed placeholder JWT secret.** `config.py:17` defaults `JWT_SECRET="change-me-in-production"`. `backend/.env` contains a real secret **but nothing loads it** — there is no `load_dotenv`/pydantic-settings anywhere (`requirements.txt` has no dotenv dep; `config.py` uses bare `os.getenv`). So unless the process is launched with an explicit env export, tokens are signed with a publicly known string → **anyone can forge an admin token**. Worse, `backend/.env` is **not gitignored** (`.gitignore` only excludes `.env.production`), so the real secret + DB password are one `git add .` away from being committed.

**MED**
- **`get_current_user_id` trusts tokens for non-existent/inactive users** (see §4). Deactivating a user does not revoke their access on 8 routers.
- **Info disclosure:** `GET /gamification/users/{id}/points` and `/users/{id}/badges` take an arbitrary `user_id` with no ownership check — any user can read anyone's balance/badges.

**LOW**
- SQL injection surface: **effectively none.** Heavy `db.execute(text(...))` but all *values* are bound params. The only interpolated SQL is the PATCH `set_clause` built from `updates` keys — those keys are constrained to Pydantic model fields, not raw input, and values are bound. Safe **by convention**; flag it because a future careless edit that feeds user strings as column names would open injection.
- SSE `/environmental/events` is intentionally unauthenticated; payload is ids/metrics only. Acceptable, documented.
- `seed.py:64` falls back to **SHA-256** password hashing if the `bcrypt` import fails — seeded users would then be un-loginable (login uses `bcrypt.checkpw`, which raises on a non-bcrypt hash). Latent footgun.
- `requirements.txt` is fully **unpinned** — reproducibility risk for a graded build.

---

## 6. Frontend / UX gaps

7 screens; wiring status:

| Screen | Live data | Gaps |
|---|---|---|
| Dashboard | ✅ `GET /dashboard/summary` | "Recent Activity" is **mock** (`dashboardMock`); live-badge **broken** (SSE route mismatch). |
| Environmental | ✅ goals/factors/products/carbon/ledger (read) | **No write UI at all** — cannot log an emission, the app's core action. |
| Social | ✅ activities/categories/participants; **join + verify are live writes** | Verify button visible to everyone (no role gating in UI *or* server). |
| Governance | ✅ policies/audits/issues/ledger/verify (read) | Read-only; no acknowledge / create UI. |
| Gamification | ✅ challenges/badges/rewards/leaderboard; **redeem + join live** | — |
| Reports | ✅ available/recent/generate (real file download) | Department dropdown uses **mock** (`departmentsMock`); framework/scope/data-tier filters are **cosmetic** (never sent). |
| Settings | ✅ settings get/patch; notifications list/mark-read | — |

- **Signup is fully mock (`auth.ts:49`)** despite `POST /auth/signup` existing on the backend. It writes a fake `mock.<id>.<ts>` token to localStorage; every subsequent authenticated API call then **401s / errors**. A judge who "creates an account" sees a broken app.
- Validation feedback: present on Login/Signup (field errors) and Settings (weights-sum guard). Reasonable.
- Empty/error states: `useApi` handles loading/error with Retry, and even special-cases 404 → "Endpoint not implemented." Good.
- Color scheme is consistent (E/S/G score cards, quick-action classes). No obvious broken layouts found.

---

## 7. What will break during the live demo (ranked)

1. **The "live closed loop" won't be live.** FE hits `/notifications/stream` (404) and there's no log-emission form. → *Mitigation:* repoint `useNotificationsStream` at `/environmental/events` with event names `carbon.created`/`score.updated`, **and** add a log form — or demo the loop via API/curl and narrate it.
2. **"Sign up" mid-demo → broken session.** Mock token → every call errors. → *Mitigation:* only ever log in with seeded creds (`ceo@bharti.in` / `bharti@123`); don't touch Signup.
3. **Config drift on startup.** `.env` says db `ecosphere_db` + `postgresql://`, but `config.py` defaults to db `ecosphere` + `postgresql+psycopg2://`, and `.env` isn't auto-loaded. Wrong launch method → connection failure or wrong secret. → *Mitigation:* confirm the effective `DATABASE_URL` before going on stage; the app as-is uses the `ecosphere` DB.
4. **A judge logs in as an employee and edits a policy / verifies their own CSR / self-awards points.** Server allows it. → *Mitigation:* add role guards (fix #2 below); short-term, don't hand a judge an employee login.
5. **A DB-savvy judge challenges the "immutable ledger."** Owner bypasses the `REVOKE`; hash omits metadata. → *Mitigation:* be ready to explain, or land the trigger (fix #6).

---

## 8. Top 10 fixes before submission (ranked by impact × cheapness)

### Must-fix
1. **Reconnect the live SSE.** `frontend/src/hooks/useNotificationsStream.ts` — point `EventSource` at `${API_BASE}/environmental/events` and listen for `carbon.created` / `score.updated` (or add a `GET /notifications/stream` alias in `notifications.py`). *Impact: restores the flagship differentiator. Cost: ~10 lines.*
2. **Add role guards to the `auth_dep` write endpoints.** In `csr.py`, `challenges.py`, `governance.py`, `gamification.py`, `social.py`, replace `get_current_user_id` on POST/PATCH (especially participation-verify and challenge-complete) with a manager/admin check. Fastest path: give `auth_dep` a `require_manager_id` variant, or switch these routers to `core.deps.require_manager`. *Kills self-approval points farming and governance tampering. Cost: a few lines per route.*
3. **Fix the JWT secret.** `config.py` — load `backend/.env` (add `python-dotenv` + `load_dotenv()`), and **remove the `change-me-in-production` default** so a missing secret fails fast. Add `backend/.env` to `.gitignore`. *Stops trivial admin-token forgery. Cost: tiny.*
4. **Wire Signup to the real endpoint.** `frontend/src/auth.ts` + `Signup.tsx` — call `POST /auth/signup` (it already returns a token + user). Delete the mock branch. *Prevents a broken demo account. Cost: ~15 lines.*
5. **Add a "Log Emission" form.** `frontend/src/api/endpoints.ts` + `Environmental.tsx` — POST `/environmental/operational-records`. *Makes the closed loop demonstrable in the browser; without it the core workflow has no UI. Cost: one form.*

### Nice-to-have
6. **Make the ledger actually immutable + hash the metadata.** `schema.sql` — add a `BEFORE UPDATE OR DELETE ON esg_ledger` trigger that `RAISE EXCEPTION` (owner-proof, unlike REVOKE). `services/ledger.py` — fold `entry_type`/`ref_table`/`ref_id`/`actor_user_id` into `compute_row_hash`. *Closes the two integrity holes in differentiator (a).*
7. **Close the redemption balance race.** `rewards.py` — lock the user's point rows (`… FOR UPDATE`) or take a `pg_advisory_xact_lock(user_id)` before the balance check. *Prevents overspend on concurrent redeems.*
8. **Refresh Social score after point awards.** `csr.py` / `challenges.py` — call `scoring.refresh_department_score` after `award_points`. *Makes gamification move the dashboard consistently.*
9. **Harden `get_current_user_id`.** `auth_dep.py` — verify the user exists and `is_active`, mirroring `core.deps`. Better: consolidate the two auth dependencies into one. *Fixes deactivated-user access on 8 routers.*
10. **Housekeeping.** Drop/stop writing `users.points_balance`; pin `requirements.txt`; raise a POLICY notification somewhere so rule #5 is fully satisfied; delete the SHA-256 seed fallback. *Cheap credibility wins.*

---

Audit complete, ready for review
