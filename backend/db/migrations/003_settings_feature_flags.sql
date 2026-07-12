-- ============================================================================
-- Migration 003: move feature toggles into the settings table
-- ----------------------------------------------------------------------------
-- Safe to apply to an already-running database WITHOUT wiping data: additive
-- columns with sensible defaults. Run once against the live DB, e.g.:
--     psql "$DATABASE_URL" -f backend/db/migrations/003_settings_feature_flags.sql
--
-- These replace the previously hardcoded EVIDENCE_REQUIRED / AUTO_AWARD_BADGES
-- constants and the unread AUTO_EMISSION_CALC env var; they are now read from
-- settings (row id=1) at call time and editable via PATCH /api/settings.
-- ============================================================================

ALTER TABLE settings ADD COLUMN IF NOT EXISTS evidence_required  BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE settings ADD COLUMN IF NOT EXISTS auto_award_badges  BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE settings ADD COLUMN IF NOT EXISTS auto_emission_calc BOOLEAN NOT NULL DEFAULT TRUE;
