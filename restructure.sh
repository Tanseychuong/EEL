#!/usr/bin/env bash
# EEL backend restructure + scaffold script
# Run from the repo root (where backend/ and frontend/ already exist):
#   chmod +x restructure.sh && ./restructure.sh
#
# This does three things:
#   1. Renames the pre-pivot blueprint folders (content -> opportunities, progress -> saved)
#   2. Creates the new files from the restructuring plan (permissions.py, pagination.py, services.py, tests/)
#   3. Writes the already-built code into app/__init__.py, app/cli.py, .env.example, docs/PLAN.md
#      (models.py, extensions.py, config.py, manage.py, wsgi.py, requirements.txt, seed.py are
#      rewritten too, so this script is safe to re-run and produces the same result each time)

set -e

cd backend

# --- Step 1: rename pre-pivot blueprint folders --------------------------
if [ -d "app/blueprints/content" ] && [ ! -d "app/blueprints/opportunities" ]; then
  git mv app/blueprints/content app/blueprints/opportunities
  echo "Renamed content/ -> opportunities/"
fi
if [ -d "app/blueprints/progress" ] && [ ! -d "app/blueprints/saved" ]; then
  git mv app/blueprints/progress app/blueprints/saved
  echo "Renamed progress/ -> saved/"
fi

# --- Step 2: create new directories --------------------------------------
mkdir -p app/blueprints/auth app/blueprints/opportunities app/blueprints/saved app/blueprints/admin
mkdir -p migrations tests docs

# --- Step 3: write files --------------------------------------------------

mkdir -p "$(dirname "app/models.py")"
cat > app/models.py << 'EOF_EEL_SCAFFOLD'
"""
Empower & Elevate Leaders (EEL) — Database Models (Opportunity Portal)

Users post opportunities (jobs, internships, scholarships, grants, etc.),
admins approve them before they go live, and premium users get early access
to newly-approved listings before free users do.

Design decisions:
- OpportunityCategory is a table, not an enum, so admins can add new
  opportunity types without a code change.
- Moderation state lives directly on Opportunity (status + reviewer fields)
  rather than a separate audit table — one review step doesn't need its own
  history table yet.
- Premium "early access" is a time window, not a hard content split: every
  approved opportunity gets published_at (premium sees it now) and
  free_access_at (published_at + EARLY_ACCESS_WINDOW, when free users can
  see it too). is_visible_to() is the one place that rule lives.
- Indexes are added on every column that list/filter/admin-queue queries
  will actually filter or sort by — added now, not retrofitted later,
  since adding them to a live table with real data is a slower migration.
"""

from datetime import datetime, timedelta
import enum
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Index
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db

# How long free users wait after an opportunity is approved before they see
# it. Premium users see it immediately at approval. Also exposed as
# config.EARLY_ACCESS_HOURS — keep the two in sync, or read this from config
# in approve() if you want it adjustable without a deploy.
EARLY_ACCESS_WINDOW = timedelta(hours=48)


def gen_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"


class OpportunityStatus(enum.Enum):
    PENDING = "pending"      # awaiting admin review
    APPROVED = "approved"    # live (subject to early-access window)
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER, index=True)

    # Premium status kept as simple fields rather than a subscriptions table
    # for now — add PremiumSubscription (with payment references) later if/
    # when billing is wired up. is_premium_active() is the one method that
    # should be called everywhere else, so that later change stays contained.
    is_premium = db.Column(db.Boolean, default=False, nullable=False, index=True)
    premium_expires_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    opportunities_posted = db.relationship(
        "Opportunity", back_populates="posted_by",
        foreign_keys="Opportunity.posted_by_id",
        cascade="all, delete-orphan",
    )
    saved_opportunities = db.relationship(
        "SavedOpportunity", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def is_premium_active(self) -> bool:
        """The single source of truth for 'does this user get early access'."""
        if not self.is_premium:
            return False
        if self.premium_expires_at is None:
            return True  # no expiry set = indefinite premium (e.g. admin-granted)
        return self.premium_expires_at > datetime.utcnow()

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role.value,
            "is_premium": self.is_premium_active(),
        }


# ---------------------------------------------------------------------------
# Opportunity categories (admin-manageable, not hard-coded)
# ---------------------------------------------------------------------------

class OpportunityCategory(db.Model):
    __tablename__ = "opportunity_categories"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slug = db.Column(db.String(50), unique=True, nullable=False)   # 'jobs', 'scholarships'
    name = db.Column(db.String(120), nullable=False)               # 'Jobs & Internships'
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, index=True)

    opportunities = db.relationship("Opportunity", back_populates="category")


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

class Opportunity(db.Model):
    __tablename__ = "opportunities"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)

    posted_by_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False, index=True)
    category_id = db.Column(UUID(as_uuid=False), db.ForeignKey("opportunity_categories.id"), nullable=False, index=True)

    title = db.Column(db.String(200), nullable=False)
    organization = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200))                # nullable: remote/unspecified
    opportunity_url = db.Column(db.String(500))          # external application link
    application_deadline = db.Column(db.DateTime, index=True)

    # --- Moderation ------------------------------------------------------
    status = db.Column(db.Enum(OpportunityStatus), nullable=False, default=OpportunityStatus.PENDING, index=True)
    submitted_at = db.Column(db.DateTime, server_default=db.func.now())
    reviewed_by_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)

    # --- Premium early access ---------------------------------------------
    published_at = db.Column(db.DateTime, index=True)      # set on approval; premium sees it now
    free_access_at = db.Column(db.DateTime, index=True)    # published_at + EARLY_ACCESS_WINDOW

    posted_by = db.relationship("User", back_populates="opportunities_posted", foreign_keys=[posted_by_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])
    category = db.relationship("OpportunityCategory", back_populates="opportunities")
    saved_by = db.relationship("SavedOpportunity", back_populates="opportunity", cascade="all, delete-orphan")

    # Composite indexes matching the actual list-page queries:
    # "approved opportunities in category X, newest first" and
    # "approved opportunities visible to free users, newest first".
    __table_args__ = (
        Index("ix_opportunities_status_category", "status", "category_id"),
        Index("ix_opportunities_status_free_access", "status", "free_access_at"),
        Index("ix_opportunities_status_published", "status", "published_at"),
    )

    def approve(self, admin_user: "User") -> None:
        """Admin approves a pending opportunity: goes live for premium users
        now, and for free users after EARLY_ACCESS_WINDOW."""
        now = datetime.utcnow()
        self.status = OpportunityStatus.APPROVED
        self.reviewed_by_id = admin_user.id
        self.reviewed_at = now
        self.published_at = now
        self.free_access_at = now + EARLY_ACCESS_WINDOW

    def reject(self, admin_user: "User", reason: str) -> None:
        self.status = OpportunityStatus.REJECTED
        self.reviewed_by_id = admin_user.id
        self.reviewed_at = datetime.utcnow()
        self.rejection_reason = reason

    def is_visible_to(self, user: "User") -> bool:
        """Approval + access-window check in one place, so every endpoint
        that lists opportunities applies the same rule."""
        if self.status != OpportunityStatus.APPROVED:
            return False
        now = datetime.utcnow()
        if user.is_premium_active():
            return self.published_at is not None and self.published_at <= now
        return self.free_access_at is not None and self.free_access_at <= now

    @staticmethod
    def visible_query_for(user: "User"):
        """Returns a SQLAlchemy query filter (not a Python-side check) for
        listing endpoints, so visibility filtering happens in the database
        and stays index-backed instead of loading every row to check it."""
        now = datetime.utcnow()
        base = Opportunity.query.filter(Opportunity.status == OpportunityStatus.APPROVED)
        if user is not None and user.is_premium_active():
            return base.filter(Opportunity.published_at <= now)
        return base.filter(Opportunity.free_access_at <= now)


class SavedOpportunity(db.Model):
    """A user bookmarking an opportunity to revisit later."""
    __tablename__ = "saved_opportunities"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False, index=True)
    opportunity_id = db.Column(UUID(as_uuid=False), db.ForeignKey("opportunities.id"), nullable=False, index=True)
    saved_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", back_populates="saved_opportunities")
    opportunity = db.relationship("Opportunity", back_populates="saved_by")

    __table_args__ = (
        db.UniqueConstraint("user_id", "opportunity_id", name="uq_saved_user_opportunity"),
    )
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/extensions.py")"
cat > app/extensions.py << 'EOF_EEL_SCAFFOLD'
"""
Flask extension instances, initialized without an app (the app factory in
app/__init__.py calls .init_app() on each). Keeping these here — separate
from models.py — is what lets models.py, blueprints, and the factory all
import `db` without circular-import issues.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

# Rate limiting protects the opportunity-submission and auth endpoints from
# abuse. Storage defaults to in-memory (fine for one dev/small instance);
# point RATELIMIT_STORAGE_URI at Redis once you're running more than one
# backend process, since in-memory limits don't share state across processes.
limiter = Limiter(key_func=get_remote_address)
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "config.py")"
cat > config.py << 'EOF_EEL_SCAFFOLD'
"""
Environment-driven configuration. Nothing here is hard-coded so the same
codebase runs in dev, test, and production off different env vars —
required for deploying frontend/backend separately (Vercel + Render/Railway)
and for ever running more than one backend instance.
"""

import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://localhost:5432/eel"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection pooling — matters once you have concurrent requests, so it's
    # configured from day one rather than left on SQLAlchemy's defaults.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 20)),
        "pool_pre_ping": True,       # avoids "server closed the connection" errors
        "pool_recycle": 280,         # recycle before most providers' idle timeout
    }

    # Auth
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Pagination — every list endpoint (opportunities, admin queues) should
    # read these rather than hard-coding page sizes, so one place controls
    # payload size as the dataset grows.
    DEFAULT_PAGE_SIZE = int(os.environ.get("DEFAULT_PAGE_SIZE", 20))
    MAX_PAGE_SIZE = int(os.environ.get("MAX_PAGE_SIZE", 100))

    # Premium early-access window — mirrors models.EARLY_ACCESS_WINDOW but
    # exposed as config too, in case you want it adjustable without a deploy.
    EARLY_ACCESS_HOURS = int(os.environ.get("EARLY_ACCESS_HOURS", 48))

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Rate limiting storage — "memory://" is fine for a single process;
    # swap to a Redis URL once you run more than one backend instance,
    # or limits stop being shared across processes.
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL", "sqlite:///:memory:"
    )
    # SQLite has no connection pool in the same sense — drop the Postgres-only options
    SQLALCHEMY_ENGINE_OPTIONS = {}


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self):
        # Fail fast in production if secrets were left on their dev defaults.
        assert os.environ.get("SECRET_KEY"), "SECRET_KEY must be set in production"
        assert os.environ.get("JWT_SECRET_KEY"), "JWT_SECRET_KEY must be set in production"
        assert os.environ.get("DATABASE_URL"), "DATABASE_URL must be set in production"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/__init__.py")"
cat > app/__init__.py << 'EOF_EEL_SCAFFOLD'
"""
Flask application factory. create_app() is what wsgi.py, manage.py, and
tests all call — nothing outside this file should import a global `app`.
"""

import os
import logging

from flask import Flask, jsonify

from config import config_by_name
from app.extensions import db, migrate, jwt, cors, limiter


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_cli(app)
    _configure_logging(app)

    @app.get("/health")
    def health():
        # Cheap liveness check — point your host's health check / uptime
        # monitor here rather than at a real endpoint.
        return jsonify(status="ok"), 200

    return app


def _init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    limiter.init_app(app)


def _register_blueprints(app):
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.opportunities.routes import opportunities_bp
    from app.blueprints.saved.routes import saved_bp
    from app.blueprints.admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(opportunities_bp, url_prefix="/api/opportunities")
    app.register_blueprint(saved_bp, url_prefix="/api/saved")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Not found"), 404

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error=str(e.description) if hasattr(e, "description") else "Bad request"), 400

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify(error="Too many requests, slow down"), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled server error")
        return jsonify(error="Internal server error"), 500


def _register_cli(app):
    from app.cli import register_commands
    register_commands(app)


def _configure_logging(app):
    if not app.debug and not app.testing:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/cli.py")"
cat > app/cli.py << 'EOF_EEL_SCAFFOLD'
"""
Custom management commands, registered onto Flask's built-in CLI (the same
one Flask-Migrate's `db` commands attach to). Reachable as:

    python manage.py create-admin
    python manage.py list-pending
    python manage.py grant-premium <email>

These are the operational tasks that come up running a moderated, tiered
platform day-to-day — not one-off dev scripts (that's what seed.py is for).
"""

import click
from flask.cli import with_appcontext

from app.extensions import db
from models import User, UserRole, Opportunity, OpportunityStatus


def register_commands(app):
    app.cli.add_command(create_admin)
    app.cli.add_command(list_pending)
    app.cli.add_command(grant_premium)


@click.command("create-admin")
@click.option("--name", prompt=True)
@click.option("--email", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def create_admin(name, email, password):
    """Create an admin user — the first account, since no one can approve
    opportunities (or grant themselves admin) without one existing."""
    if User.query.filter_by(email=email).first():
        click.echo(f"A user with email {email} already exists.")
        return

    user = User(name=name, email=email, role=UserRole.ADMIN)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Admin user created: {email}")


@click.command("list-pending")
@with_appcontext
def list_pending():
    """List opportunities awaiting moderation — a CLI fallback for the
    admin dashboard, useful before that UI exists or if it's ever down."""
    pending = Opportunity.query.filter_by(status=OpportunityStatus.PENDING).all()
    if not pending:
        click.echo("Nothing pending review.")
        return
    for opp in pending:
        click.echo(f"[{opp.id}] {opp.title} — submitted by {opp.posted_by.email}")


@click.command("grant-premium")
@click.argument("email")
@click.option("--days", default=None, type=int, help="Expire after N days (omit for indefinite).")
@with_appcontext
def grant_premium(email, days):
    """Manually grant premium — the operational stand-in until a payment
    flow exists."""
    from datetime import datetime, timedelta

    user = User.query.filter_by(email=email).first()
    if not user:
        click.echo(f"No user found with email {email}.")
        return

    user.is_premium = True
    user.premium_expires_at = (
        datetime.utcnow() + timedelta(days=days) if days else None
    )
    db.session.commit()
    expiry_note = f"for {days} days" if days else "indefinitely"
    click.echo(f"Granted premium to {email} ({expiry_note}).")
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "manage.py")"
cat > manage.py << 'EOF_EEL_SCAFFOLD'
#!/usr/bin/env python
"""
Standard management entry point.

    python manage.py run                          # dev server
    python manage.py db init / migrate / upgrade   # Flask-Migrate (Alembic)
    python manage.py create-admin                  # bootstrap the first admin
    python manage.py list-pending                  # moderation queue, CLI-side
    python manage.py grant-premium user@example.com

This works because app.cli is Flask's own click Group — calling it runs
the full set of built-in + extension + custom commands with the app
context already handled, so nothing here needs FLASK_APP set separately.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.cli()
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "wsgi.py")"
cat > wsgi.py << 'EOF_EEL_SCAFFOLD'
"""
Production WSGI entry point. Point your server at this, e.g.:

    gunicorn "wsgi:app" --workers 4 --bind 0.0.0.0:8000

Workers > 1 is why RATELIMIT_STORAGE_URI and any future caching need to be
Redis-backed rather than in-memory once you deploy — in-memory state isn't
shared across worker processes.
"""

from app import create_app

app = create_app(config_name="production")
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "requirements.txt")"
cat > requirements.txt << 'EOF_EEL_SCAFFOLD'
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.7
Flask-JWT-Extended==4.6.0
Flask-CORS==4.0.1
Flask-Limiter==3.8.0
psycopg2-binary==2.9.9
python-dotenv==1.0.1
gunicorn==22.0.0
marshmallow==3.21.3
click==8.1.7
pytest==8.3.2
pytest-flask==1.3.0
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "seed.py")"
cat > seed.py << 'EOF_EEL_SCAFFOLD'
"""
Seed script for EEL's opportunity portal — populates opportunity categories,
a demo admin + regular user, and a few sample opportunities in different
moderation states so the early-access logic has something real to test
against.

Run with:  python seed.py
"""

from datetime import datetime, timedelta

from app import create_app
from app.extensions import db
from models import (
    User, UserRole,
    OpportunityCategory,
    Opportunity, OpportunityStatus,
)

app = create_app()

with app.app_context():
    # --- Categories ----------------------------------------------------
    categories = {
        "jobs": OpportunityCategory(slug="jobs", name="Jobs & Internships"),
        "scholarships": OpportunityCategory(slug="scholarships", name="Scholarships & Grants"),
        "fellowships": OpportunityCategory(slug="fellowships", name="Fellowships"),
        "competitions": OpportunityCategory(slug="competitions", name="Competitions"),
    }
    db.session.add_all(categories.values())
    db.session.flush()

    # --- Users -----------------------------------------------------------
    admin = User(name="Admin User", email="admin@eel.dev", role=UserRole.ADMIN)
    admin.set_password("change-me")

    poster = User(name="Ama Owusu", email="ama@eel.dev", role=UserRole.USER)
    poster.set_password("change-me")

    premium_user = User(
        name="Kojo Mensah", email="kojo@eel.dev", role=UserRole.USER,
        is_premium=True,  # indefinite premium (no expiry) for easy local testing
    )
    premium_user.set_password("change-me")

    db.session.add_all([admin, poster, premium_user])
    db.session.flush()

    # --- Sample opportunities, in different states ------------------------
    now = datetime.utcnow()

    approved_visible_to_all = Opportunity(
        posted_by_id=poster.id,
        category_id=categories["jobs"].id,
        title="Junior Software Developer",
        organization="Accra Tech Hub",
        description="Entry-level role building web apps with a small team.",
        location="Accra, Ghana (hybrid)",
        opportunity_url="https://example.com/jobs/junior-dev",
        application_deadline=now + timedelta(days=30),
    )
    approved_visible_to_all.approve(admin)
    # Backdate so the early-access window has already passed for free users too.
    approved_visible_to_all.published_at = now - timedelta(hours=72)
    approved_visible_to_all.free_access_at = now - timedelta(hours=24)

    approved_premium_only = Opportunity(
        posted_by_id=poster.id,
        category_id=categories["scholarships"].id,
        title="Ashesi Merit Scholarship",
        organization="Ashesi University",
        description="Full-tuition scholarship for incoming CS students.",
        opportunity_url="https://example.com/scholarships/ashesi-merit",
        application_deadline=now + timedelta(days=45),
    )
    approved_premium_only.approve(admin)  # published_at = now; free_access_at = now + 48h

    pending_review = Opportunity(
        posted_by_id=poster.id,
        category_id=categories["fellowships"].id,
        title="Youth Leadership Fellowship",
        organization="Global Citizens Network",
        description="A 6-month fellowship for early-career civic leaders.",
        application_deadline=now + timedelta(days=60),
    )
    # left as PENDING — demonstrates the moderation queue

    rejected_example = Opportunity(
        posted_by_id=poster.id,
        category_id=categories["competitions"].id,
        title="Suspicious Prize Giveaway",
        organization="Unverified Org",
        description="Missing verifiable details.",
    )
    rejected_example.reject(admin, reason="Organization could not be verified.")

    db.session.add_all([
        approved_visible_to_all, approved_premium_only,
        pending_review, rejected_example,
    ])
    db.session.commit()

    print("Seed complete:")
    print(f"  {len(categories)} categories")
    print("  3 users (1 admin, 1 regular, 1 premium) — password for all: change-me")
    print("  4 opportunities: 1 visible to everyone, 1 in premium early-access "
          "window, 1 pending, 1 rejected")
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname ".env.example")"
cat > .env.example << 'EOF_EEL_SCAFFOLD'
# Flask
FLASK_ENV=development
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me-too

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/eel
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Pagination
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100

# Premium
EARLY_ACCESS_HOURS=48

# CORS — comma-separated origins allowed to call the API
CORS_ORIGINS=http://localhost:5173

# Rate limiting — "memory://" for single-process dev; a Redis URL once you
# run more than one backend worker/instance
RATELIMIT_STORAGE_URI=memory://
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "docs/PLAN.md")"
cat > docs/PLAN.md << 'EOF_EEL_SCAFFOLD'
# EEL — Opportunity Portal: Implementation Plan

## 1. Where things actually stand (checked against the GitHub repo)

| File | Status |
|---|---|
| `backend/app/models.py` | ✅ pushed, matches the opportunity-portal schema |
| `backend/app/extensions.py` | ✅ pushed |
| `backend/config.py` | ✅ pushed |
| `backend/manage.py`, `wsgi.py`, `requirements.txt`, `seed.py` | ✅ pushed |
| `backend/app/__init__.py` | ❌ still the empty scaffold placeholder |
| `backend/app/cli.py` | ❌ not in the repo yet |
| `backend/.env.example` | ❌ not in the repo yet |
| `backend/app/blueprints/auth/*` | empty placeholders (as expected — not built yet) |
| `backend/app/blueprints/content/`, `backend/app/blueprints/progress/` | still exist from the pre-pivot scaffold — leftover, need renaming/removing |
| `backend/app/blueprints/opportunities/` | doesn't exist yet |
| `backend/app/blueprints/admin/*` | empty placeholder |

**Immediate blocker:** `app/__init__.py`'s factory imports `app.blueprints.opportunities.routes` and `app.cli` — neither exists yet, so the app won't start until the rename below happens and `cli.py` is added. This has to happen before any route code is written.

## 2. User access levels

Four tiers, from least to most privileged. Every endpoint's behavior should be defined in terms of these, not ad hoc per-route checks:

| Tier | Can do |
|---|---|
| **Anonymous** | View the public marketing site only. No opportunity data. |
| **Free user** (registered) | Browse approved opportunities *after* the early-access window; submit new opportunities (goes to pending); save/unsave opportunities; manage own profile |
| **Premium user** | Everything Free can do, plus: see approved opportunities immediately (no early-access wait) |
| **Admin** | Everything, plus: approve/reject pending opportunities; manage categories; manage users (view, grant/revoke premium, promote to admin) |

This maps directly onto `models.py` already: `User.role` (USER/ADMIN) and `User.is_premium_active()` are the two checks every protected endpoint needs — nothing else to invent.

**Implementation mechanism:** a `permissions.py` module (new — see structure below) with decorators `@login_required`, `@admin_required`, and a `visible_opportunities_for(user)` query helper (already stubbed as `Opportunity.visible_query_for()` in models.py) — so the access rule is enforced once, not re-implemented per route.

## 3. Restructured file layout

```
backend/
├── app/
│   ├── __init__.py            # factory (needs pushing)
│   ├── extensions.py          # ✅ done
│   ├── models.py              # ✅ done
│   ├── cli.py                 # needs pushing
│   ├── permissions.py         # NEW — role/premium decorators, shared across blueprints
│   ├── pagination.py          # NEW — one helper: paginate(query, schema) -> dict, used by every list endpoint
│   │
│   ├── blueprints/
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py          # /register /login /refresh /me
│   │   │   └── schemas.py         # marshmallow: RegisterSchema, LoginSchema
│   │   │
│   │   ├── opportunities/         # RENAME from content/ — public-facing CRUD + browsing
│   │   │   ├── __init__.py
│   │   │   ├── routes.py          # GET list (role-aware), GET one, POST submit, PATCH own-pending, DELETE own-pending
│   │   │   ├── schemas.py         # OpportunitySchema, OpportunityCreateSchema
│   │   │   └── services.py        # NEW — business logic (visibility rules, submission validation) kept out of routes.py
│   │   │
│   │   ├── saved/                 # NEW — split out of the old progress/ folder
│   │   │   ├── __init__.py
│   │   │   └── routes.py          # POST/DELETE save, GET my-saved
│   │   │
│   │   └── admin/
│   │       ├── __init__.py
│   │       ├── routes.py          # moderation queue, approve/reject, category CRUD, user mgmt
│   │       └── schemas.py
│   │
├── migrations/                # Flask-Migrate (run `flask db init` once __init__.py is live)
├── tests/
│   ├── conftest.py             # NEW — app fixture using TestingConfig + sqlite
│   ├── test_auth.py
│   ├── test_opportunities.py
│   └── test_admin.py
├── config.py                   # ✅ done
├── manage.py                   # ✅ done
├── wsgi.py                     # ✅ done
├── seed.py                     # ✅ done
├── requirements.txt            # ✅ done (add pytest, pytest-flask for the tests/ folder)
└── .env.example                # needs pushing
```

**What's changing and why:**
- `content/` → `opportunities/`, `progress/` retired in favor of a smaller `saved/` blueprint (bookmarking is the only thing `progress` ever needed to do post-pivot — no reason to keep the old name or the extra surface area).
- `services.py` inside `opportunities/` — route handlers should stay thin (parse request → call service → serialize response). Business logic like "is this submission complete enough to go to review" or "apply the visibility filter" lives in one testable place instead of being copy-pasted across route functions as the API grows.
- `permissions.py` and `pagination.py` at the `app/` level (not inside one blueprint) because every blueprint needs both.
- `tests/` — not present in the original scaffold at all. Worth having from the start given moderation + tiered access is exactly the kind of logic that silently breaks when one blueprint changes and nobody notices it affected another.

## 4. Build order

Each phase is small enough to commit and check independently — matching how we've been working.

**Phase 0 — Unblock the app**
1. Push `app/__init__.py`, `app/cli.py`, `.env.example` (already written, just need committing)
2. `git mv backend/app/blueprints/content backend/app/blueprints/opportunities`
3. `git mv backend/app/blueprints/progress backend/app/blueprints/saved` (or delete and recreate — either works)
4. Confirm `flask run` boots without import errors (it'll 404 everywhere until routes exist, but it should *start*)

**Phase 1 — Auth**
- `POST /api/auth/register`, `POST /api/auth/login` (issues JWT access + refresh), `POST /api/auth/refresh`, `GET /api/auth/me`
- `permissions.py`: `@login_required`, `@admin_required`
- This has to come first — nothing else is testable without a logged-in user

**Phase 2 — Opportunities (read + submit)**
- `GET /api/opportunities` — paginated, applies `Opportunity.visible_query_for(current_user)`, filterable by category
- `GET /api/opportunities/<id>` — single item, same visibility check
- `POST /api/opportunities` — any logged-in user submits (status defaults to PENDING)
- `PATCH/DELETE /api/opportunities/<id>` — only the original poster, only while still PENDING

**Phase 3 — Saved opportunities**
- `POST/DELETE /api/opportunities/<id>/save`, `GET /api/saved` — small, but exercises the many-to-many relationship end to end

**Phase 4 — Admin**
- `GET /api/admin/opportunities/pending` — the moderation queue
- `POST /api/admin/opportunities/<id>/approve`, `POST /api/admin/opportunities/<id>/reject`
- `GET/POST /api/admin/categories` — category management
- `GET /api/admin/users`, `POST /api/admin/users/<id>/grant-premium` — the API equivalent of the `grant-premium` CLI command, for when there's a real admin UI instead of a terminal

**Phase 5 — Frontend wiring**
- Only after the API is stable: `apiClient.js`, `AuthContext.jsx`, then the learner-facing routes (`Dashboard`, `ModuleView` → repurposed as opportunity browsing/detail views), then the admin routes

## 5. Scalability notes (beyond what's already in `models.py`/`config.py`)

- **Pagination is mandatory, not optional**, on every list endpoint from day one — `config.DEFAULT_PAGE_SIZE`/`MAX_PAGE_SIZE` already exist; `pagination.py` should be the only place that turns a query into a page.
- **Category list is a good caching candidate** — it changes rarely (admin-managed) but gets read on every opportunity list/submit. Flask-Caching with a short TTL (or invalidated on admin category writes) avoids a repeated join for data that's effectively static.
- **Rate limiting is already wired (`Flask-Limiter`)** — apply it specifically to `POST /api/opportunities` (submission spam) and `POST /api/auth/login` (credential stuffing) once those routes exist.
- **Redis, not memory, for rate-limit storage and any caching**, the moment you run more than one backend process (`RATELIMIT_STORAGE_URI` in `.env` is already set up for this swap).
- **Full-text search** on opportunity title/description isn't in the schema yet — if search becomes a real feature, Postgres's built-in `tsvector` (via a generated column + GIN index) is the low-effort option before reaching for Elasticsearch.

---
*Next concrete step: Phase 0 — push the three missing files and do the blueprint rename, so the app can actually boot.*
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/auth/__init__.py")"
cat > app/blueprints/auth/__init__.py << 'EOF_EEL_SCAFFOLD'

EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/auth/routes.py")"
cat > app/blueprints/auth/routes.py << 'EOF_EEL_SCAFFOLD'
from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

# POST /register, POST /login, POST /refresh, GET /me — Phase 1
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/auth/schemas.py")"
cat > app/blueprints/auth/schemas.py << 'EOF_EEL_SCAFFOLD'
"""Marshmallow schemas for auth request/response validation (Phase 1)."""
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/opportunities/__init__.py")"
cat > app/blueprints/opportunities/__init__.py << 'EOF_EEL_SCAFFOLD'

EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/opportunities/routes.py")"
cat > app/blueprints/opportunities/routes.py << 'EOF_EEL_SCAFFOLD'
from flask import Blueprint

opportunities_bp = Blueprint("opportunities", __name__)

# GET /, GET /<id>, POST /, PATCH /<id>, DELETE /<id> — Phase 2
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/opportunities/schemas.py")"
cat > app/blueprints/opportunities/schemas.py << 'EOF_EEL_SCAFFOLD'
"""Marshmallow schemas: OpportunitySchema, OpportunityCreateSchema (Phase 2)."""
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/opportunities/services.py")"
cat > app/blueprints/opportunities/services.py << 'EOF_EEL_SCAFFOLD'
"""
Business logic for opportunities, kept out of routes.py so it's testable
on its own and reusable (e.g. from the admin blueprint or a future CLI
command) without duplicating the rules.

Phase 2 will add functions here such as:
    submit_opportunity(user, data) -> Opportunity
    list_visible_opportunities(user, category=None, page=1) -> Pagination
"""
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/saved/__init__.py")"
cat > app/blueprints/saved/__init__.py << 'EOF_EEL_SCAFFOLD'

EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/saved/routes.py")"
cat > app/blueprints/saved/routes.py << 'EOF_EEL_SCAFFOLD'
from flask import Blueprint

saved_bp = Blueprint("saved", __name__)

# POST /<opportunity_id>, DELETE /<opportunity_id>, GET / — Phase 3
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/admin/__init__.py")"
cat > app/blueprints/admin/__init__.py << 'EOF_EEL_SCAFFOLD'

EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/admin/routes.py")"
cat > app/blueprints/admin/routes.py << 'EOF_EEL_SCAFFOLD'
from flask import Blueprint

admin_bp = Blueprint("admin", __name__)

# GET /opportunities/pending, POST /opportunities/<id>/approve,
# POST /opportunities/<id>/reject, GET/POST /categories,
# GET /users, POST /users/<id>/grant-premium — Phase 4
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/blueprints/admin/schemas.py")"
cat > app/blueprints/admin/schemas.py << 'EOF_EEL_SCAFFOLD'
"""Marshmallow schemas for admin endpoints (Phase 4)."""
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/permissions.py")"
cat > app/permissions.py << 'EOF_EEL_SCAFFOLD'
"""
Shared access-control decorators, applied on top of Flask-JWT-Extended's
@jwt_required(). One place for the four-tier access model from PLAN.md:
Anonymous / Free / Premium / Admin.

Phase 1 will fill these in, e.g.:

    from functools import wraps
    from flask_jwt_extended import jwt_required, get_jwt_identity
    from models import User

    def login_required(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper

    def admin_required(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user = User.query.get(get_jwt_identity())
            if not user or not user.is_admin():
                return {"error": "Admin access required"}, 403
            return fn(*args, **kwargs)
        return wrapper
"""
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "app/pagination.py")"
cat > app/pagination.py << 'EOF_EEL_SCAFFOLD'
"""
Single shared helper so every list endpoint paginates the same way,
reading limits from config.DEFAULT_PAGE_SIZE / config.MAX_PAGE_SIZE
rather than hard-coding page sizes per route.

Phase 2 will fill this in, e.g.:

    from flask import current_app, request

    def paginate(query, schema):
        page = request.args.get("page", 1, type=int)
        per_page = min(
            request.args.get("per_page", current_app.config["DEFAULT_PAGE_SIZE"], type=int),
            current_app.config["MAX_PAGE_SIZE"],
        )
        result = query.paginate(page=page, per_page=per_page, error_out=False)
        return {
            "items": schema.dump(result.items, many=True),
            "page": result.page,
            "per_page": result.per_page,
            "total": result.total,
            "pages": result.pages,
        }
"""
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "tests/conftest.py")"
cat > tests/conftest.py << 'EOF_EEL_SCAFFOLD'
"""
Shared pytest fixtures. Phase 0 checkpoint: this file existing and
`pytest` collecting with zero errors confirms the app factory + models
import cleanly under TestingConfig (sqlite in-memory).
"""

import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture
def app():
    app = create_app(config_name="testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "tests/test_auth.py")"
cat > tests/test_auth.py << 'EOF_EEL_SCAFFOLD'
"""Phase 1 tests: register, login, refresh, /me."""
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "tests/test_opportunities.py")"
cat > tests/test_opportunities.py << 'EOF_EEL_SCAFFOLD'
"""Phase 2 tests: submit, list visibility (free vs premium vs admin), pagination."""
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "tests/test_admin.py")"
cat > tests/test_admin.py << 'EOF_EEL_SCAFFOLD'
"""Phase 4 tests: approve/reject, category CRUD, grant-premium."""
EOF_EEL_SCAFFOLD

mkdir -p "$(dirname "migrations/.gitkeep")"
cat > migrations/.gitkeep << 'EOF_EEL_SCAFFOLD'

EOF_EEL_SCAFFOLD

echo "EEL backend restructure complete."
echo "Next: pip install -r requirements.txt  &&  python manage.py create-admin"
