-- ============================================================================
-- EEL — Opportunity Portal — PostgreSQL Schema
-- ============================================================================
-- Hand-written reference matching backend/app/models.py exactly.
--
-- This is NOT what actually runs in production — Flask-Migrate/Alembic
-- generates the real, versioned migrations from models.py
-- (`flask db init && flask db migrate && flask db upgrade`). Keep this file
-- in sync manually whenever models.py changes; it's for:
--   - quick local setup without going through Flask at all (`psql -f schema.sql`)
--   - reviewing the schema without reading Python
--   - onboarding: a new contributor can read table/column intent in one place
--
-- Run against an empty database:
--   createdb eel
--   psql -d eel -f schema.sql
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- provides gen_random_uuid()

-- ----------------------------------------------------------------------------
-- Enums
-- ----------------------------------------------------------------------------

CREATE TYPE user_role AS ENUM ('user', 'admin');
CREATE TYPE opportunity_status AS ENUM ('pending', 'approved', 'rejected');

-- ----------------------------------------------------------------------------
-- users
-- ----------------------------------------------------------------------------

CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(120) NOT NULL,
    email               VARCHAR(255) NOT NULL UNIQUE,
    password_hash       VARCHAR(255) NOT NULL,
    role                user_role NOT NULL DEFAULT 'user',

    -- Premium status: simple fields for now, not a subscriptions table.
    -- is_premium_active() in models.py is the single source of truth for
    -- whether early access applies (handles indefinite vs. time-limited).
    is_premium          BOOLEAN NOT NULL DEFAULT FALSE,
    premium_expires_at  TIMESTAMP,

    created_at          TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_role ON users (role);
CREATE INDEX ix_users_is_premium ON users (is_premium);

-- ----------------------------------------------------------------------------
-- opportunity_categories
-- ----------------------------------------------------------------------------
-- A table, not an enum, so admins can add categories (e.g. "Volunteer")
-- without a schema change.

CREATE TABLE opportunity_categories (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug         VARCHAR(50) NOT NULL UNIQUE,     -- 'jobs', 'scholarships'
    name         VARCHAR(120) NOT NULL,           -- 'Jobs & Internships'
    description  TEXT,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX ix_opportunity_categories_is_active ON opportunity_categories (is_active);

-- ----------------------------------------------------------------------------
-- opportunities
-- ----------------------------------------------------------------------------

CREATE TABLE opportunities (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    posted_by_id         UUID NOT NULL REFERENCES users(id),
    category_id          UUID NOT NULL REFERENCES opportunity_categories(id),

    title                VARCHAR(200) NOT NULL,
    organization         VARCHAR(200),
    description          TEXT NOT NULL,
    location             VARCHAR(200),                -- NULL = remote/unspecified
    opportunity_url      VARCHAR(500),                 -- external application link
    application_deadline TIMESTAMP,

    -- Moderation: lives directly on the row rather than a separate audit
    -- table, since a single review step doesn't need its own history yet.
    status               opportunity_status NOT NULL DEFAULT 'pending',
    submitted_at         TIMESTAMP NOT NULL DEFAULT now(),
    reviewed_by_id       UUID REFERENCES users(id),
    reviewed_at          TIMESTAMP,
    rejection_reason     TEXT,

    -- Premium early access: two timestamps, not a duplicated content pool.
    -- published_at  = when premium users can see it (set at approval)
    -- free_access_at = published_at + EARLY_ACCESS_WINDOW (48h by default,
    --                   see models.EARLY_ACCESS_WINDOW / config.EARLY_ACCESS_HOURS)
    published_at         TIMESTAMP,
    free_access_at       TIMESTAMP
);

CREATE INDEX ix_opportunities_posted_by_id ON opportunities (posted_by_id);
CREATE INDEX ix_opportunities_category_id ON opportunities (category_id);
CREATE INDEX ix_opportunities_application_deadline ON opportunities (application_deadline);
CREATE INDEX ix_opportunities_status ON opportunities (status);
CREATE INDEX ix_opportunities_published_at ON opportunities (published_at);
CREATE INDEX ix_opportunities_free_access_at ON opportunities (free_access_at);

-- Composite indexes matching the actual list-page queries:
-- "approved opportunities in category X, newest first" and
-- "approved opportunities visible to free/premium users, newest first".
CREATE INDEX ix_opportunities_status_category ON opportunities (status, category_id);
CREATE INDEX ix_opportunities_status_free_access ON opportunities (status, free_access_at);
CREATE INDEX ix_opportunities_status_published ON opportunities (status, published_at);

-- ----------------------------------------------------------------------------
-- saved_opportunities  (bookmarks)
-- ----------------------------------------------------------------------------

CREATE TABLE saved_opportunities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    opportunity_id  UUID NOT NULL REFERENCES opportunities(id),
    saved_at        TIMESTAMP NOT NULL DEFAULT now(),

    CONSTRAINT uq_saved_user_opportunity UNIQUE (user_id, opportunity_id)
);

CREATE INDEX ix_saved_opportunities_user_id ON saved_opportunities (user_id);
CREATE INDEX ix_saved_opportunities_opportunity_id ON saved_opportunities (opportunity_id);

-- ============================================================================
-- End of schema
-- ============================================================================
