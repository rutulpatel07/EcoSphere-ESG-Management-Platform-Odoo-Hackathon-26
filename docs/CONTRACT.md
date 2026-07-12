# EcoSphere API Contract

**Base URL:** `http://localhost:8000/api`
**Auth:** Bearer JWT in `Authorization: Bearer <token>` (except `/auth/login`).
**Content-Type:** `application/json` for all request and response bodies.

This document is authoritative. Do **not** rename fields, routes, or enums.
Routers are currently stubbed with a single `GET /ping` returning
`{ "ok": true, "module": "<name>" }`; the endpoints below are the target
contract to implement within each owner zone.

Enums:
- `category_type`: `CSR` | `CHALLENGE`
- `user_role`: `ADMIN` | `MANAGER` | `EMPLOYEE`
- `op_type`: `PURCHASE` | `MANUFACTURING` | `EXPENSE` | `FLEET`
- `data_tier`: `MEASURED` | `CALCULATED` | `ESTIMATED` | `DEFAULT`
- `challenge_lifecycle`: `Draft` | `Active` | `UnderReview` | `Completed` | `Archived`

---

## Meta

### `GET /health`
No auth. Liveness probe.
```json
// 200
{ "status": "ok", "app": "EcoSphere ESG Management Platform" }
```

---

## Auth — `/auth`

### `POST /auth/login`
```json
// request
{ "email": "admin@ecosphere.io", "password": "secret" }
```
```json
// 200
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@ecosphere.io",
    "full_name": "Ada Admin",
    "role": "ADMIN",
    "department_id": 1,
    "points_balance": 0
  }
}
```
```json
// 401
{ "detail": "Invalid credentials" }
```

### `GET /auth/me`
Returns the current user (from JWT).
```json
// 200
{ "id": 1, "email": "admin@ecosphere.io", "full_name": "Ada Admin", "role": "ADMIN", "department_id": 1, "points_balance": 0 }
```

---

## Users — `/users`

### `GET /users`
Query: `?role=EMPLOYEE&department_id=2`
```json
// 200
[
  { "id": 5, "email": "amara@ecosphere.io", "full_name": "Amara Osei", "role": "EMPLOYEE", "department_id": 4, "points_balance": 2480, "is_active": true }
]
```

### `POST /users`
```json
// request
{ "email": "new@ecosphere.io", "full_name": "New Person", "password": "secret", "role": "EMPLOYEE", "department_id": 2 }
```
```json
// 201
{ "id": 42, "email": "new@ecosphere.io", "full_name": "New Person", "role": "EMPLOYEE", "department_id": 2, "points_balance": 0, "is_active": true }
```

### `GET /users/{id}` · `PATCH /users/{id}` · `DELETE /users/{id}`
`PATCH` accepts any subset of `{ full_name, role, department_id, is_active }`.

---

## Departments — `/departments`

### `GET /departments`
Returns the hierarchy (parent_id links).
```json
// 200
[
  { "id": 1, "name": "Company", "code": "ROOT", "parent_id": null, "manager_id": 1 },
  { "id": 2, "name": "Operations", "code": "OPS", "parent_id": 1, "manager_id": 3 }
]
```

### `POST /departments`
```json
// request
{ "name": "Logistics", "code": "LOG", "parent_id": 2, "manager_id": 7 }
```
```json
// 201
{ "id": 8, "name": "Logistics", "code": "LOG", "parent_id": 2, "manager_id": 7, "created_at": "2026-07-12T09:00:00Z" }
```

### `GET /departments/{id}` · `PATCH /departments/{id}` · `DELETE /departments/{id}`

---

## Dashboard — `/dashboard`

### `GET /dashboard/summary`
```json
// 200
{
  "esgScore": { "total": 78.4, "e": 82.1, "s": 74.6, "g": 76.0, "weights": { "E": 40, "S": 30, "G": 30 } },
  "kpis": [
    { "label": "Total Emissions (tCO2e)", "value": "1,284", "delta": "-6.2%", "trend": "down" }
  ],
  "emissionsTrend": [
    { "month": "Jul", "scope1": 97, "scope2": 176, "scope3": 78 }
  ],
  "departmentScores": [
    { "department": "R&D", "period": "2026-Q2", "e": 88, "s": 80, "g": 82, "total": 84.0 }
  ]
}
```

---

## Environmental — `/environmental`

### Goals
`GET /environmental/goals` · `POST /environmental/goals` · `PATCH /environmental/goals/{id}`
```json
// GET 200
[
  { "id": 1, "title": "Cut Scope 1+2 by 25%", "metric": "Scope1+2 tCO2e", "baseline_value": 1710, "target_value": 1282, "current_value": 1284, "unit": "tCO2e", "department_id": null, "start_date": "2026-01-01", "target_date": "2026-12-31", "status": "ON_TRACK" }
]
```
```json
// POST request
{ "title": "80% renewable electricity", "metric": "Renewable share", "baseline_value": 32, "target_value": 80, "unit": "%", "start_date": "2026-01-01", "target_date": "2027-06-30" }
```

### Emission Factors
`GET /environmental/emission-factors` · `POST /environmental/emission-factors`
Uniqueness: `(activity_type, version)`.
```json
// GET 200
[
  { "id": 11, "activity_type": "grid_electricity_uk", "unit": "kgCO2e/kWh", "factor_value": 0.20705, "source": "DEFRA 2024", "version": 2, "valid_from": "2024-01-01", "valid_to": null, "uncertainty_pct": 5.0 }
]
```
```json
// POST request
{ "activity_type": "grid_electricity_uk", "unit": "kgCO2e/kWh", "factor_value": 0.19338, "source": "DEFRA 2025", "version": 3, "valid_from": "2025-01-01", "uncertainty_pct": 4.5 }
```

### Operational Records
`GET /environmental/operational-records` · `POST /environmental/operational-records`
Posting a record triggers a matching `carbon_transaction` (factor snapshotted).
```json
// POST request
{ "op_type": "FLEET", "department_id": 8, "activity_type": "diesel_fleet", "quantity": 1800, "unit": "litre", "reference": "VAN-14", "occurred_on": "2026-06-28" }
```
```json
// 201
{ "id": 990, "op_type": "FLEET", "activity_type": "diesel_fleet", "quantity": 1800, "unit": "litre", "occurred_on": "2026-06-28", "carbon_transaction_id": 502 }
```

### Carbon Transactions
`GET /environmental/carbon-transactions`
```json
// 200
[
  { "id": 502, "operational_record_id": 990, "emission_factor_id": 12, "factor_value_used": 2.6871, "factor_version_used": 2, "quantity": 1800, "co2e_kg": 4836.8, "scope": 1, "data_tier": "CALCULATED", "uncertainty_pct": 3.5, "department_id": 8, "occurred_on": "2026-06-28" }
]
```

### Product ESG Profiles
`GET /environmental/products` · `POST /environmental/products`
```json
// GET 200
[
  { "id": 90, "sku": "ECO-BTL-500", "name": "rPET Water Bottle 500ml", "embodied_carbon_kg": 0.084, "recyclable_pct": 100, "water_usage_l": 1.4, "ethical_score": 86, "certifications": ["B-Corp", "FSC"] }
]
```

---

## Social — `/social`

### Categories
`GET /social/categories?type=CSR` · `POST /social/categories`
```json
// GET 200
[ { "id": 1, "name": "Community Outreach", "type": "CSR", "is_active": true } ]
```

### CSR Activities
`GET /social/activities` · `POST /social/activities` · `PATCH /social/activities/{id}`
```json
// GET 200
[
  { "id": 301, "title": "Riverside Cleanup Drive", "category_id": 2, "department_id": 2, "location": "Riverside Park", "points_reward": 150, "capacity": 40, "start_date": "2026-07-20", "end_date": null, "status": "OPEN" }
]
```

### Participation
`GET /social/activities/{id}/participants` · `POST /social/activities/{id}/join` · `PATCH /social/participation/{id}`
Unique on `(csr_activity_id, user_id)`.
```json
// POST /join request
{ "proof_url": "https://files.local/proof/7001.jpg" }
```
```json
// PATCH request (verify)
{ "status": "VERIFIED", "hours": 4 }
```
```json
// participants 200
[
  { "id": 7001, "csr_activity_id": 301, "user_id": 5, "proof_url": "https://files.local/proof/7001.jpg", "status": "VERIFIED", "hours": 4, "verified_by": 3 }
]
```

---

## Governance — `/governance`

### Policies
`GET /governance/policies` · `POST /governance/policies`
```json
// GET 200
[
  { "id": 40, "title": "Anti-Bribery & Corruption Policy", "version": 3, "category": "Governance", "is_mandatory": true, "effective_date": "2026-01-01" }
]
```

### Policy Acknowledgements
`POST /governance/policies/{id}/acknowledge` · `GET /governance/policies/{id}/acknowledgements`
Unique on `(policy_id, user_id)`.
```json
// POST 201
{ "id": 4412, "policy_id": 40, "user_id": 5, "acknowledged_at": "2026-06-29T09:03:00Z" }
```

### Audits
`GET /governance/audits` · `POST /governance/audits` · `PATCH /governance/audits/{id}`
```json
// GET 200
[
  { "id": 12, "title": "GRI Annual Assurance 2026", "framework": "GRI", "status": "IN_PROGRESS", "auditor_user_id": 3, "period_start": "2026-01-01", "period_end": "2026-06-30", "scheduled_date": "2026-08-15" }
]
```

### Compliance Issues
`GET /governance/compliance-issues` · `POST /governance/compliance-issues` · `PATCH /governance/compliance-issues/{id}`
`owner_user_id` and `due_date` are required.
```json
// POST request
{ "audit_id": 12, "title": "Missing Scope 3 supplier data", "severity": "HIGH", "owner_user_id": 3, "due_date": "2026-07-31" }
```
```json
// GET 200
[
  { "id": 88, "audit_id": 12, "title": "Missing Scope 3 supplier data", "severity": "HIGH", "status": "OPEN", "owner_user_id": 3, "due_date": "2026-07-31", "resolved_at": null }
]
```

### ESG Ledger (read-only, append-only)
`GET /governance/ledger` · `GET /governance/ledger/verify`
```json
// ledger 200
[
  { "seq": 10232, "entry_type": "POLICY", "ref_table": "policy_acknowledgements", "ref_id": 4412, "prev_hash": "9f2c...c31", "row_hash": "b1d9...aa8", "actor_user_id": 5, "created_at": "2026-06-29T09:03:00Z" }
]
```
```json
// verify 200
{ "valid": true, "entries": 10232, "broken_at_seq": null }
```

---

## Gamification — `/gamification`

### Challenges
`GET /gamification/challenges` · `POST /gamification/challenges` · `PATCH /gamification/challenges/{id}`
Lifecycle transitions via `PATCH { "lifecycle": "Active" }`.
```json
// GET 200
[
  { "id": 601, "title": "Bike-to-Work Fortnight", "category_id": 3, "lifecycle": "Active", "goal_metric": "commute_km_by_bike", "goal_target": 5000, "points_reward": 300, "badge_id": 21, "start_date": "2026-07-14", "end_date": "2026-07-26" }
]
```

### Challenge Participation
`POST /gamification/challenges/{id}/join` · `PATCH /gamification/challenge-participation/{id}`
Unique on `(challenge_id, user_id)`.
```json
// PATCH request (progress)
{ "progress": 42, "status": "IN_PROGRESS", "proof_url": null }
```

### Badges
`GET /gamification/badges` · `POST /gamification/badges` · `GET /gamification/users/{id}/badges`
```json
// badges 200
[
  { "id": 21, "name": "Carbon Cutter", "description": "Log 12 months of measured data", "icon": "🌿", "tier": "Gold", "unlock_rule": { "type": "streak", "months": 12 }, "points_value": 500, "is_active": true }
]
```

### Rewards & Redemptions
`GET /gamification/rewards` · `POST /gamification/rewards` · `POST /gamification/rewards/{id}/redeem` · `GET /gamification/redemptions`
Redeem decrements `stock` and creates a negative `point_transaction`.
```json
// rewards 200
[ { "id": 31, "name": "Reusable Coffee Kit", "description": "...", "cost_points": 400, "stock": 24, "is_active": true } ]
```
```json
// redeem 201
{ "id": 8801, "user_id": 5, "reward_id": 31, "points_spent": 400, "status": "PENDING", "created_at": "2026-07-11T15:20:00Z" }
```
```json
// redeem 409
{ "detail": "Out of stock" }
```

### Points & Leaderboard
`GET /gamification/leaderboard` · `GET /gamification/users/{id}/points`
```json
// leaderboard 200
[ { "rank": 1, "user_id": 5, "user": "Amara Osei", "department": "R&D", "points": 2480 } ]
```
```json
// points 200
{ "balance": 2480, "transactions": [ { "id": 1, "points": 150, "reason": "CSR: Riverside Cleanup", "created_at": "2026-06-20T10:00:00Z" } ] }
```

---

## Reports — `/reports`

### `GET /reports/available`
```json
// 200
[ { "id": "esg-summary", "name": "ESG Summary Report", "formats": ["PDF", "XLSX"] } ]
```

### `POST /reports/generate`
```json
// request
{ "report_id": "esg-summary", "format": "PDF", "period": "2026-Q2" }
```
Returns the file stream (`application/pdf` or the XLSX mime type) with
`Content-Disposition: attachment`. Metadata is also recorded and listed by:

### `GET /reports/recent`
```json
// 200
[ { "id": 5001, "name": "ESG Summary Report — Q2 2026", "format": "PDF", "generated_at": "2026-07-01T10:00:00Z", "size_kb": 842 } ]
```

---

## Settings — `/settings`

### `GET /settings`
Returns the singleton row.
```json
// 200
{ "id": 1, "gamification_enabled": true, "csr_module_enabled": true, "notifications_enabled": true, "public_leaderboard": true, "esg_weights": { "E": 40, "S": 30, "G": 30 }, "updated_at": "2026-07-10T08:00:00Z" }
```

### `PATCH /settings`
Accepts any subset of the four toggles and/or `esg_weights`.
`esg_weights` values must sum to 100.
```json
// request
{ "gamification_enabled": false, "esg_weights": { "E": 50, "S": 25, "G": 25 } }
```
```json
// 200 -> updated settings object (same shape as GET)
```

---

## Notifications — `/notifications`

### `GET /notifications`
Query: `?unread=true`
```json
// 200
[
  { "id": 9001, "user_id": 5, "title": "New compliance issue assigned", "body": "Missing Scope 3 supplier data is due 2026-07-31.", "type": "COMPLIANCE", "link": "/governance", "is_read": false, "created_at": "2026-07-11T12:00:00Z" }
]
```

### `POST /notifications/{id}/read`
```json
// 200
{ "id": 9001, "is_read": true }
```

### `GET /notifications/stream`
Server-Sent Events (`text/event-stream`). Each event `data:` payload is a
notification object with the same shape as `GET /notifications` items.
```
event: notification
data: { "id": 9003, "title": "Reward approved", "type": "REWARD", "is_read": false, "created_at": "2026-07-12T09:10:00Z" }
```
