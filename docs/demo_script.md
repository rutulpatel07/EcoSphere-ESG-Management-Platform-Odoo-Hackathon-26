# EcoSphere Demo: 2-Minute Flow with Tamper Detection

**Audience**: Stakeholders, auditors, regulators.

**Goal**: Show real-time ESG capture, factor versioning, and ledger integrity verification.

**Time**: ~2 minutes (automated steps); ~3–4 minutes with Q&A.

---

## Setup

Assume backend is running on `http://localhost:8000`, database is live, demo user exists:
- Email: `demo@ecosphere.io`
- Password: `demo123`
- Role: `MANAGER`

---

## Part 1: Login & Dashboard (20 seconds)

**Narrator**: "EcoSphere is a real-time ESG platform. Every action is auditable. Let's log in."

```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@ecosphere.io", "password": "demo123"}' | jq '.access_token' -r > /tmp/token.txt

TOKEN=$(cat /tmp/token.txt)
echo "✓ Logged in as demo@ecosphere.io"
```

**Show**: Screenshot of the dashboard showing:
- ESG Score (total, E/S/G breakdown)
- Emissions Trend (chart)
- Department Scores

**Narrator**: "ESG score is updated in real-time as operational data flows in."

---

## Part 2: Post an Operational Record (30 seconds)

**Narrator**: "Let's capture a real activity: fleet fuel usage. The system snapshots the emission factor *at the moment of measurement*."

```bash
TOKEN=$(cat /tmp/token.txt)

# Check current emission factor for diesel fleet
echo "📊 Current emission factor for diesel_fleet:"
curl -s -X GET "http://localhost:8000/api/environmental/emission-factors?activity_type=diesel_fleet" \
  -H "Authorization: Bearer $TOKEN" | jq '.[0] | {id, factor_value, version, valid_from}'

# Post an operational record (1800 liters of diesel, today)
echo ""
echo "📝 Posting operational record: 1800L diesel fleet usage..."
RECORD=$(curl -s -X POST http://localhost:8000/api/environmental/operational-records \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "op_type": "FLEET",
    "department_id": 1,
    "activity_type": "diesel_fleet",
    "quantity": 1800,
    "unit": "litre",
    "reference": "DEMO-VAN-001",
    "occurred_on": "2026-07-12"
  }')

RECORD_ID=$(echo $RECORD | jq '.id')
TXN_ID=$(echo $RECORD | jq '.carbon_transaction_id')
echo "✓ Record ID: $RECORD_ID, Transaction ID: $TXN_ID"
```

**Show**: Screenshot of the carbon_transaction showing:
- factor_value_used: 2.6871 kgCO2e/L
- factor_version_used: 2 (locked at this moment)
- co2e_kg: ~4836.8
- data_tier: CALCULATED

**Narrator**: "The factor version is locked in. Even if we update the factor next month, this June record stays the same. It's immutable."

---

## Part 3: Create Compliance Issue (20 seconds)

**Narrator**: "Now let's trace the audit trail. We create a compliance issue, which automatically logs to the governance ledger."

```bash
TOKEN=$(cat /tmp/token.txt)

echo "🔒 Creating compliance issue (triggers ledger entry)..."
ISSUE=$(curl -s -X POST http://localhost:8000/api/governance/compliance-issues \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audit_id": 1,
    "title": "Demo: Scope 3 supplier data collection",
    "severity": "MEDIUM",
    "owner_user_id": 1,
    "due_date": "2026-08-12"
  }')

ISSUE_ID=$(echo $ISSUE | jq '.id')
echo "✓ Compliance Issue ID: $ISSUE_ID"
echo ""
echo "📋 Checking ledger for entry..."
curl -s -X GET "http://localhost:8000/api/governance/ledger?ref_table=compliance_issues&ref_id=$ISSUE_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.[0] | {seq, entry_type, ref_id, prev_hash, row_hash}' | head -20
```

**Show**: Screenshot showing:
- seq: 10233 (or latest)
- entry_type: COMPLIANCE_ISSUE
- prev_hash, row_hash (SHA-256 hashes)

**Narrator**: "Every entry points back to the previous one via a hash. Tamper with one, and the chain breaks."

---

## Part 4: Verify the Chain (10 seconds)

```bash
TOKEN=$(cat /tmp/token.txt)

echo "✅ Verifying ledger integrity..."
curl -s -X GET http://localhost:8000/api/governance/ledger/verify \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**Expected output**:
```json
{ "valid": true, "entries": 10233, "broken_at_seq": null }
```

**Narrator**: "Chain is valid. All 10k+ entries are intact."

---

## Part 5: The Tamper Stunt (30 seconds)

**Narrator**: "Now, let's simulate an attack. An insider tries to cover up a compliance issue by modifying the database directly."

```bash
# Connect to PostgreSQL and tamper with entry seq 10230
echo "⚠️  Simulating database tampering (insider attack)..."
psql -U postgres -d ecosphere_dev -c "
  UPDATE esg_ledger
  SET row_hash = 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'
  WHERE seq = 10230;
" 2>/dev/null

echo "🔓 Successfully tampered with ledger entry seq 10230."
echo ""
echo "🔍 Re-running verification..."
TOKEN=$(cat /tmp/token.txt)
curl -s -X GET http://localhost:8000/api/governance/ledger/verify \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**Expected output**:
```json
{ "valid": false, "entries": 10233, "broken_at_seq": 10231 }
```

**Narrator**: "The chain is broken at seq 10231. We know exactly where tampering occurred and that the records after it are compromised. You can't hide in the ledger."

---

## Fallback Plan: Recovery

**Narrator**: "In a real incident, here's how we respond."

### Step 1: Identify Compromise Scope
```bash
psql -U postgres -d ecosphere_dev -c "
  SELECT seq, entry_type, ref_table, ref_id, created_at
  FROM esg_ledger
  WHERE seq >= 10230
  ORDER BY seq;
" | head -20
```

Pinpoint which entries are affected.

### Step 2: Restore from Backup
```bash
# Restore the database to the last known-good backup (before seq 10230)
# Example: backup from 2026-07-12 10:00 AM
pg_restore -U postgres -d ecosphere_dev < /backups/ecosphere_2026-07-12_1000.dump
```

### Step 3: Re-enter Lost Data
```bash
# Manually re-issue the compliance issues that were lost
# (timestamps & actor IDs from the incident log, if available)
curl -s -X POST http://localhost:8000/api/governance/compliance-issues \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audit_id": 1,
    "title": "Demo: Scope 3 supplier data collection (re-entered)",
    "severity": "MEDIUM",
    "owner_user_id": 1,
    "due_date": "2026-08-12"
  }'
```

### Step 4: Verify Restored Chain
```bash
TOKEN=$(cat /tmp/token.txt)
curl -s -X GET http://localhost:8000/api/governance/ledger/verify \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**Expected**: `valid: true` again.

### Step 5: Audit Log & Report
- Document the incident (timestamp, affected seq range, root cause)
- File a compliance report (attach the broken ledger screenshot)
- Notify auditors & board

---

## Part 6: Factor Versioning in Action (20 seconds)

**Narrator**: "One more thing: science evolves. When emission factors update, old records stay locked, new records use the new factor."

```bash
TOKEN=$(cat /tmp/token.txt)

echo "📊 Publishing a new emission factor version (DEFRA 2025)..."
NEW_FACTOR=$(curl -s -X POST http://localhost:8000/api/environmental/emission-factors \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "activity_type": "diesel_fleet",
    "unit": "kgCO2e/L",
    "factor_value": 2.5100,
    "source": "DEFRA 2025",
    "version": 3,
    "valid_from": "2025-01-01",
    "uncertainty_pct": 4.2
  }')

echo "✓ New factor created (version 3, value 2.5100)"
echo ""
echo "📈 Recalculating ESG score..."
curl -s -X GET http://localhost:8000/api/dashboard/summary \
  -H "Authorization: Bearer $TOKEN" | jq '.esgScore'
```

**Show**: ESG score may shift slightly (old emissions keep old factor, new ones use new factor).

**Narrator**: "The score is honest. It reflects both old and new data, so you can see the impact of factor updates."

---

## Q&A Script

**Q: Isn't immutability too rigid?**
A: "Measured data is immutable. Calculated data can be re-measured with new factors. We distinguish via data_tier. Auditors see the full trail."

**Q: What if we need to fix a typo in a compliance issue title?**
A: "Create a correction record in the ledger (new entry). Never overwrite. Auditors see the fix and its timestamp."

**Q: How do we recompute ESG when factors change?**
A: "Nightly batch job (optional, not built yet). Aggregates across all carbon_transactions grouped by data_tier & factor_version."

---

## Timeline

| Time | Step |
|------|------|
| 0:00 | Login & show dashboard |
| 0:20 | Post operational record & show factor lock-in |
| 0:50 | Create compliance issue, show ledger entry |
| 1:00 | Verify chain (valid) |
| 1:10 | Tamper & re-verify (broken) |
| 1:40 | Recovery plan (restore, re-enter, verify) |
| 2:00 | Factor versioning, ESG score update |
| 2:30–4:00 | Q&A |

---

## Notes for Operator

- **Backup before demo**: Ensure a recent backup exists (for restoration step)
- **Token caching**: Save the JWT to `/tmp/token.txt` to avoid re-auth
- **Database user**: Ensure psql user has permissions (or use `sudo -u postgres`)
- **Network**: If running remotely, adjust `localhost:8000` to the actual server IP
- **Slideshow**: Pair curl commands with screenshots/UI captures for clarity
- **Timing**: Use `time` command to measure each section; rehearse once

---

**Demo created**: 2026-07-12  
**Next review**: 2026-08-12 (quarterly refresh for new factors/ledger entries)
