-- ============================================================================
-- Migration 002: append-only trigger for esg_ledger
-- ----------------------------------------------------------------------------
-- Safe to apply to an already-running database WITHOUT wiping data: it only
-- (re)creates a function and a trigger. Run once against the live DB, e.g.:
--     psql "$DATABASE_URL" -f backend/db/migrations/002_ledger_trigger.sql
--
-- Effect: any UPDATE or DELETE on esg_ledger raises, so the hash-chained ledger
-- stays truly append-only even for the table owner (who the schema's
-- REVOKE UPDATE, DELETE ... FROM PUBLIC does not constrain).
-- ============================================================================

CREATE OR REPLACE FUNCTION esg_ledger_append_only()
    RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'esg_ledger is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_esg_ledger_append_only ON esg_ledger;
CREATE TRIGGER trg_esg_ledger_append_only
    BEFORE UPDATE OR DELETE ON esg_ledger
    FOR EACH ROW EXECUTE FUNCTION esg_ledger_append_only();
