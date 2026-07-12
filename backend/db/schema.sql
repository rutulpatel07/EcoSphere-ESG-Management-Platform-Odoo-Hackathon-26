-- ============================================================================
-- EcoSphere ESG Management Platform — Full Database Schema
-- Target: PostgreSQL 16
-- This file is authoritative. Do NOT rename fields, tables, or enums.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid(), digest()

-- ---------------------------------------------------------------------------
-- Enum types
-- ---------------------------------------------------------------------------
DROP TYPE IF EXISTS category_type       CASCADE;
DROP TYPE IF EXISTS user_role           CASCADE;
DROP TYPE IF EXISTS op_type             CASCADE;
DROP TYPE IF EXISTS data_tier           CASCADE;
DROP TYPE IF EXISTS challenge_lifecycle CASCADE;

CREATE TYPE category_type       AS ENUM ('CSR', 'CHALLENGE');
CREATE TYPE user_role           AS ENUM ('ADMIN', 'MANAGER', 'EMPLOYEE');
CREATE TYPE op_type             AS ENUM ('PURCHASE', 'MANUFACTURING', 'EXPENSE', 'FLEET');
CREATE TYPE data_tier           AS ENUM ('MEASURED', 'CALCULATED', 'ESTIMATED', 'DEFAULT');
CREATE TYPE challenge_lifecycle AS ENUM ('Draft', 'Active', 'UnderReview', 'Completed', 'Archived');

-- ===========================================================================
-- 1. departments (self-referencing hierarchy)
-- ===========================================================================
CREATE TABLE departments (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(160) NOT NULL,
    code        VARCHAR(40)  UNIQUE,
    parent_id   INTEGER      REFERENCES departments(id) ON DELETE SET NULL,
    manager_id  INTEGER,                       -- FK to users added after users table
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_departments_parent_id  ON departments(parent_id);
CREATE INDEX idx_departments_manager_id ON departments(manager_id);
CREATE INDEX idx_departments_created_at ON departments(created_at);

-- ===========================================================================
-- 2. categories (CSR / CHALLENGE)
-- ===========================================================================
CREATE TABLE categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(160)  NOT NULL,
    type        category_type NOT NULL,
    description TEXT,
    icon        VARCHAR(80),
    is_active   BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX idx_categories_type       ON categories(type);
CREATE INDEX idx_categories_created_at ON categories(created_at);

-- ===========================================================================
-- 3. emission_factors (versioned, time-bounded)
-- ===========================================================================
CREATE TABLE emission_factors (
    id            SERIAL PRIMARY KEY,
    activity_type VARCHAR(120)   NOT NULL,
    unit          VARCHAR(40)    NOT NULL,          -- e.g. kgCO2e/kWh
    factor_value  NUMERIC(18,6)  NOT NULL,
    source        VARCHAR(200),                     -- e.g. DEFRA 2024, EPA
    version       INTEGER        NOT NULL DEFAULT 1,
    valid_from    DATE           NOT NULL,
    valid_to      DATE,                             -- NULL = currently valid
    uncertainty_pct NUMERIC(6,2),
    created_at    TIMESTAMPTZ    NOT NULL DEFAULT now(),
    CONSTRAINT uq_emission_factors_activity_version UNIQUE (activity_type, version)
);
CREATE INDEX idx_emission_factors_activity_type ON emission_factors(activity_type);
CREATE INDEX idx_emission_factors_valid_from     ON emission_factors(valid_from);
CREATE INDEX idx_emission_factors_valid_to       ON emission_factors(valid_to);
CREATE INDEX idx_emission_factors_created_at      ON emission_factors(created_at);

-- ===========================================================================
-- 4. product_esg_profiles
-- ===========================================================================
CREATE TABLE product_esg_profiles (
    id                 SERIAL PRIMARY KEY,
    sku                VARCHAR(80) UNIQUE,
    name               VARCHAR(200)  NOT NULL,
    embodied_carbon_kg NUMERIC(18,6),             -- cradle-to-gate kgCO2e/unit
    recyclable_pct     NUMERIC(6,2),
    water_usage_l      NUMERIC(18,6),
    ethical_score      NUMERIC(6,2),              -- 0-100
    certifications     JSONB        NOT NULL DEFAULT '[]'::jsonb,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_product_esg_profiles_created_at ON product_esg_profiles(created_at);

-- ===========================================================================
-- 5. environmental_goals
-- ===========================================================================
CREATE TABLE environmental_goals (
    id             SERIAL PRIMARY KEY,
    title          VARCHAR(200)  NOT NULL,
    description    TEXT,
    metric         VARCHAR(120)  NOT NULL,        -- e.g. Scope1+2 tCO2e
    baseline_value NUMERIC(18,6),
    target_value   NUMERIC(18,6) NOT NULL,
    current_value  NUMERIC(18,6) NOT NULL DEFAULT 0,
    unit           VARCHAR(40),
    department_id  INTEGER       REFERENCES departments(id) ON DELETE SET NULL,
    start_date     DATE          NOT NULL,
    target_date    DATE          NOT NULL,
    status         VARCHAR(40)   NOT NULL DEFAULT 'ON_TRACK',
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX idx_environmental_goals_department_id ON environmental_goals(department_id);
CREATE INDEX idx_environmental_goals_start_date     ON environmental_goals(start_date);
CREATE INDEX idx_environmental_goals_target_date    ON environmental_goals(target_date);
CREATE INDEX idx_environmental_goals_created_at     ON environmental_goals(created_at);

-- ===========================================================================
-- 6. esg_policies
-- ===========================================================================
CREATE TABLE esg_policies (
    id           SERIAL PRIMARY KEY,
    title        VARCHAR(200) NOT NULL,
    body         TEXT         NOT NULL,
    version      INTEGER      NOT NULL DEFAULT 1,
    category     VARCHAR(80),                     -- Environmental / Social / Governance
    is_mandatory BOOLEAN      NOT NULL DEFAULT TRUE,
    effective_date DATE       NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_esg_policies_effective_date ON esg_policies(effective_date);
CREATE INDEX idx_esg_policies_created_at      ON esg_policies(created_at);

-- ===========================================================================
-- 7. badges (unlock_rule JSONB)
-- ===========================================================================
CREATE TABLE badges (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(160) NOT NULL,
    description TEXT,
    icon        VARCHAR(80),
    tier        VARCHAR(40),                      -- Bronze / Silver / Gold / Platinum
    unlock_rule JSONB        NOT NULL DEFAULT '{}'::jsonb,
    points_value INTEGER     NOT NULL DEFAULT 0,
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_badges_created_at ON badges(created_at);

-- ===========================================================================
-- 8. rewards (with stock)
-- ===========================================================================
CREATE TABLE rewards (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(200) NOT NULL,
    description  TEXT,
    cost_points  INTEGER      NOT NULL,
    stock        INTEGER      NOT NULL DEFAULT 0,
    image_url    VARCHAR(400),
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT chk_rewards_stock_nonneg CHECK (stock >= 0)
);
CREATE INDEX idx_rewards_created_at ON rewards(created_at);

-- ===========================================================================
-- 9. users (role enum + bcrypt hash)
-- ===========================================================================
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    full_name     VARCHAR(200) NOT NULL,
    password_hash VARCHAR(72)  NOT NULL,          -- bcrypt hash
    role          user_role    NOT NULL DEFAULT 'EMPLOYEE',
    department_id INTEGER      REFERENCES departments(id) ON DELETE SET NULL,
    points_balance INTEGER     NOT NULL DEFAULT 0,
    avatar_url    VARCHAR(400),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ
);
CREATE INDEX idx_users_department_id ON users(department_id);
CREATE INDEX idx_users_role          ON users(role);
CREATE INDEX idx_users_created_at     ON users(created_at);

-- Now that users exists, wire departments.manager_id FK.
ALTER TABLE departments
    ADD CONSTRAINT fk_departments_manager
    FOREIGN KEY (manager_id) REFERENCES users(id) ON DELETE SET NULL;

-- ===========================================================================
-- 10. operational_records (op_type enum)
-- ===========================================================================
CREATE TABLE operational_records (
    id            SERIAL PRIMARY KEY,
    op_type       op_type      NOT NULL,
    department_id INTEGER      REFERENCES departments(id) ON DELETE SET NULL,
    activity_type VARCHAR(120) NOT NULL,          -- maps to emission_factors.activity_type
    quantity      NUMERIC(18,6) NOT NULL,
    unit          VARCHAR(40)  NOT NULL,
    reference     VARCHAR(200),                   -- invoice no / PO / vehicle id
    amount        NUMERIC(18,2),                  -- monetary value if EXPENSE/PURCHASE
    occurred_on   DATE         NOT NULL,
    created_by    INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_operational_records_op_type       ON operational_records(op_type);
CREATE INDEX idx_operational_records_department_id ON operational_records(department_id);
CREATE INDEX idx_operational_records_created_by    ON operational_records(created_by);
CREATE INDEX idx_operational_records_occurred_on   ON operational_records(occurred_on);
CREATE INDEX idx_operational_records_created_at    ON operational_records(created_at);

-- ===========================================================================
-- 11. carbon_transactions (factor snapshot + data_tier + uncertainty)
-- ===========================================================================
CREATE TABLE carbon_transactions (
    id                    SERIAL PRIMARY KEY,
    operational_record_id INTEGER      REFERENCES operational_records(id) ON DELETE CASCADE,
    emission_factor_id    INTEGER      REFERENCES emission_factors(id) ON DELETE SET NULL,
    factor_value_used     NUMERIC(18,6) NOT NULL,  -- snapshot of factor at calc time
    factor_version_used   INTEGER,                 -- snapshot of version
    quantity              NUMERIC(18,6) NOT NULL,
    co2e_kg               NUMERIC(18,6) NOT NULL,   -- quantity * factor_value_used
    scope                 SMALLINT,                 -- 1, 2, or 3
    data_tier             data_tier    NOT NULL DEFAULT 'ESTIMATED',
    uncertainty_pct       NUMERIC(6,2),
    department_id         INTEGER      REFERENCES departments(id) ON DELETE SET NULL,
    occurred_on           DATE         NOT NULL,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_carbon_transactions_op_record   ON carbon_transactions(operational_record_id);
CREATE INDEX idx_carbon_transactions_factor       ON carbon_transactions(emission_factor_id);
CREATE INDEX idx_carbon_transactions_department   ON carbon_transactions(department_id);
CREATE INDEX idx_carbon_transactions_occurred_on  ON carbon_transactions(occurred_on);
CREATE INDEX idx_carbon_transactions_created_at   ON carbon_transactions(created_at);

-- ===========================================================================
-- 12. esg_ledger (append-only, hash-chained)
-- ===========================================================================
CREATE TABLE esg_ledger (
    seq          BIGSERIAL PRIMARY KEY,
    entry_type   VARCHAR(80)  NOT NULL,           -- CARBON / POINTS / POLICY / AUDIT ...
    ref_table    VARCHAR(80),
    ref_id       INTEGER,
    payload      JSONB        NOT NULL DEFAULT '{}'::jsonb,
    prev_hash    CHAR(64),                         -- row_hash of previous entry
    row_hash     CHAR(64)     NOT NULL,            -- sha256 over (seq,prev_hash,payload,...)
    actor_user_id INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_esg_ledger_entry_type ON esg_ledger(entry_type);
CREATE INDEX idx_esg_ledger_ref         ON esg_ledger(ref_table, ref_id);
CREATE INDEX idx_esg_ledger_actor       ON esg_ledger(actor_user_id);
CREATE INDEX idx_esg_ledger_created_at  ON esg_ledger(created_at);

-- Enforce append-only: revoke UPDATE/DELETE from PUBLIC.
REVOKE UPDATE, DELETE ON esg_ledger FROM PUBLIC;

-- ===========================================================================
-- 13. csr_activities
-- ===========================================================================
CREATE TABLE csr_activities (
    id            SERIAL PRIMARY KEY,
    title         VARCHAR(200) NOT NULL,
    description   TEXT,
    category_id   INTEGER      REFERENCES categories(id) ON DELETE SET NULL,
    department_id INTEGER      REFERENCES departments(id) ON DELETE SET NULL,
    location      VARCHAR(200),
    points_reward INTEGER      NOT NULL DEFAULT 0,
    capacity      INTEGER,
    start_date    DATE         NOT NULL,
    end_date      DATE,
    status        VARCHAR(40)  NOT NULL DEFAULT 'OPEN',
    created_by    INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_csr_activities_category   ON csr_activities(category_id);
CREATE INDEX idx_csr_activities_department ON csr_activities(department_id);
CREATE INDEX idx_csr_activities_created_by ON csr_activities(created_by);
CREATE INDEX idx_csr_activities_start_date ON csr_activities(start_date);
CREATE INDEX idx_csr_activities_end_date   ON csr_activities(end_date);
CREATE INDEX idx_csr_activities_created_at ON csr_activities(created_at);

-- ===========================================================================
-- 14. employee_participation (UNIQUE(activity,user), proof_url)
-- ===========================================================================
CREATE TABLE employee_participation (
    id              SERIAL PRIMARY KEY,
    csr_activity_id INTEGER     NOT NULL REFERENCES csr_activities(id) ON DELETE CASCADE,
    user_id         INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    proof_url       VARCHAR(400),
    status          VARCHAR(40) NOT NULL DEFAULT 'REGISTERED',  -- REGISTERED/ATTENDED/VERIFIED/REJECTED
    hours           NUMERIC(6,2),
    verified_by     INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_employee_participation UNIQUE (csr_activity_id, user_id)
);
CREATE INDEX idx_employee_participation_activity ON employee_participation(csr_activity_id);
CREATE INDEX idx_employee_participation_user     ON employee_participation(user_id);
CREATE INDEX idx_employee_participation_verified ON employee_participation(verified_by);
CREATE INDEX idx_employee_participation_created  ON employee_participation(created_at);

-- ===========================================================================
-- 15. challenges (lifecycle enum)
-- ===========================================================================
CREATE TABLE challenges (
    id            SERIAL PRIMARY KEY,
    title         VARCHAR(200)        NOT NULL,
    description   TEXT,
    category_id   INTEGER             REFERENCES categories(id) ON DELETE SET NULL,
    lifecycle     challenge_lifecycle NOT NULL DEFAULT 'Draft',
    goal_metric   VARCHAR(120),
    goal_target   NUMERIC(18,6),
    points_reward INTEGER             NOT NULL DEFAULT 0,
    badge_id      INTEGER             REFERENCES badges(id) ON DELETE SET NULL,
    start_date    DATE                NOT NULL,
    end_date      DATE                NOT NULL,
    created_by    INTEGER             REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ         NOT NULL DEFAULT now()
);
CREATE INDEX idx_challenges_category   ON challenges(category_id);
CREATE INDEX idx_challenges_lifecycle  ON challenges(lifecycle);
CREATE INDEX idx_challenges_badge      ON challenges(badge_id);
CREATE INDEX idx_challenges_created_by ON challenges(created_by);
CREATE INDEX idx_challenges_start_date ON challenges(start_date);
CREATE INDEX idx_challenges_end_date   ON challenges(end_date);
CREATE INDEX idx_challenges_created_at ON challenges(created_at);

-- ===========================================================================
-- 16. challenge_participation
-- ===========================================================================
CREATE TABLE challenge_participation (
    id            SERIAL PRIMARY KEY,
    challenge_id  INTEGER     NOT NULL REFERENCES challenges(id) ON DELETE CASCADE,
    user_id       INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    progress      NUMERIC(18,6) NOT NULL DEFAULT 0,
    status        VARCHAR(40) NOT NULL DEFAULT 'JOINED',  -- JOINED/IN_PROGRESS/SUBMITTED/COMPLETED
    proof_url     VARCHAR(400),
    completed_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_challenge_participation UNIQUE (challenge_id, user_id)
);
CREATE INDEX idx_challenge_participation_challenge ON challenge_participation(challenge_id);
CREATE INDEX idx_challenge_participation_user      ON challenge_participation(user_id);
CREATE INDEX idx_challenge_participation_created   ON challenge_participation(created_at);

-- ===========================================================================
-- 17. point_transactions
-- ===========================================================================
CREATE TABLE point_transactions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    points      INTEGER     NOT NULL,             -- positive earn, negative spend
    reason      VARCHAR(200) NOT NULL,
    ref_table   VARCHAR(80),
    ref_id      INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_point_transactions_user       ON point_transactions(user_id);
CREATE INDEX idx_point_transactions_ref         ON point_transactions(ref_table, ref_id);
CREATE INDEX idx_point_transactions_created_at  ON point_transactions(created_at);

-- ===========================================================================
-- 18. user_badges
-- ===========================================================================
CREATE TABLE user_badges (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_id   INTEGER     NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    awarded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_badges UNIQUE (user_id, badge_id)
);
CREATE INDEX idx_user_badges_user       ON user_badges(user_id);
CREATE INDEX idx_user_badges_badge      ON user_badges(badge_id);
CREATE INDEX idx_user_badges_awarded_at ON user_badges(awarded_at);

-- ===========================================================================
-- 19. reward_redemptions
-- ===========================================================================
CREATE TABLE reward_redemptions (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reward_id    INTEGER     NOT NULL REFERENCES rewards(id) ON DELETE RESTRICT,
    points_spent INTEGER     NOT NULL,
    status       VARCHAR(40) NOT NULL DEFAULT 'PENDING',  -- PENDING/APPROVED/FULFILLED/CANCELLED
    fulfilled_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_reward_redemptions_user       ON reward_redemptions(user_id);
CREATE INDEX idx_reward_redemptions_reward     ON reward_redemptions(reward_id);
CREATE INDEX idx_reward_redemptions_created_at ON reward_redemptions(created_at);

-- ===========================================================================
-- 20. policy_acknowledgements (UNIQUE(policy,user))
-- ===========================================================================
CREATE TABLE policy_acknowledgements (
    id             SERIAL PRIMARY KEY,
    policy_id      INTEGER     NOT NULL REFERENCES esg_policies(id) ON DELETE CASCADE,
    user_id        INTEGER     NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address     VARCHAR(64),
    CONSTRAINT uq_policy_acknowledgements UNIQUE (policy_id, user_id)
);
CREATE INDEX idx_policy_acknowledgements_policy ON policy_acknowledgements(policy_id);
CREATE INDEX idx_policy_acknowledgements_user   ON policy_acknowledgements(user_id);
CREATE INDEX idx_policy_acknowledgements_at     ON policy_acknowledgements(acknowledged_at);

-- ===========================================================================
-- 21. audits
-- ===========================================================================
CREATE TABLE audits (
    id            SERIAL PRIMARY KEY,
    title         VARCHAR(200) NOT NULL,
    framework     VARCHAR(80),                    -- GRI / SASB / CSRD / ISO14001
    scope         TEXT,
    status        VARCHAR(40)  NOT NULL DEFAULT 'PLANNED',  -- PLANNED/IN_PROGRESS/COMPLETED
    auditor_user_id INTEGER    REFERENCES users(id) ON DELETE SET NULL,
    period_start  DATE,
    period_end    DATE,
    scheduled_date DATE,
    completed_date DATE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_audits_auditor        ON audits(auditor_user_id);
CREATE INDEX idx_audits_scheduled_date ON audits(scheduled_date);
CREATE INDEX idx_audits_period_start   ON audits(period_start);
CREATE INDEX idx_audits_period_end     ON audits(period_end);
CREATE INDEX idx_audits_created_at     ON audits(created_at);

-- ===========================================================================
-- 22. compliance_issues (owner_user_id NOT NULL, due_date NOT NULL)
-- ===========================================================================
CREATE TABLE compliance_issues (
    id            SERIAL PRIMARY KEY,
    audit_id      INTEGER      REFERENCES audits(id) ON DELETE SET NULL,
    title         VARCHAR(200) NOT NULL,
    description   TEXT,
    severity      VARCHAR(40)  NOT NULL DEFAULT 'MEDIUM',  -- LOW/MEDIUM/HIGH/CRITICAL
    status        VARCHAR(40)  NOT NULL DEFAULT 'OPEN',    -- OPEN/IN_PROGRESS/RESOLVED/CLOSED
    owner_user_id INTEGER      NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    due_date      DATE         NOT NULL,
    resolved_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_compliance_issues_audit    ON compliance_issues(audit_id);
CREATE INDEX idx_compliance_issues_owner    ON compliance_issues(owner_user_id);
CREATE INDEX idx_compliance_issues_due_date ON compliance_issues(due_date);
CREATE INDEX idx_compliance_issues_created  ON compliance_issues(created_at);

-- ===========================================================================
-- 23. department_scores (UNIQUE(dept,period))
-- ===========================================================================
CREATE TABLE department_scores (
    id            SERIAL PRIMARY KEY,
    department_id INTEGER      NOT NULL REFERENCES departments(id) ON DELETE CASCADE,
    period        VARCHAR(20)  NOT NULL,          -- e.g. 2026-Q2 or 2026-07
    e_score       NUMERIC(6,2) NOT NULL DEFAULT 0,
    s_score       NUMERIC(6,2) NOT NULL DEFAULT 0,
    g_score       NUMERIC(6,2) NOT NULL DEFAULT 0,
    total_score   NUMERIC(6,2) NOT NULL DEFAULT 0,
    computed_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_department_scores UNIQUE (department_id, period)
);
CREATE INDEX idx_department_scores_department ON department_scores(department_id);
CREATE INDEX idx_department_scores_computed   ON department_scores(computed_at);

-- ===========================================================================
-- 24. notifications
-- ===========================================================================
CREATE TABLE notifications (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(200) NOT NULL,
    body       TEXT,
    type       VARCHAR(60)  NOT NULL DEFAULT 'INFO',  -- INFO/ALERT/REWARD/COMPLIANCE
    link       VARCHAR(400),
    is_read    BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_user       ON notifications(user_id);
CREATE INDEX idx_notifications_is_read    ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);

-- ===========================================================================
-- 25. settings (singleton, 4 toggles + weights JSONB)
-- ===========================================================================
CREATE TABLE settings (
    id                    SMALLINT PRIMARY KEY DEFAULT 1,
    gamification_enabled  BOOLEAN  NOT NULL DEFAULT TRUE,
    csr_module_enabled    BOOLEAN  NOT NULL DEFAULT TRUE,
    notifications_enabled BOOLEAN  NOT NULL DEFAULT TRUE,
    public_leaderboard    BOOLEAN  NOT NULL DEFAULT TRUE,
    esg_weights           JSONB    NOT NULL DEFAULT '{"E":40,"S":30,"G":30}'::jsonb,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_settings_singleton CHECK (id = 1)
);

-- Seed the singleton settings row.
INSERT INTO settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
