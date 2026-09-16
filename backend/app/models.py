"""
Empower & Elevate Leaders (EEL) — Database Models (v2: Opportunity Portal)

Key design decisions:
- OpportunityCategory is a table, not an enum, so admins can add new
  opportunity types (e.g. "Fellowship", "Volunteer") without a code change.
- Moderation state lives directly on Opportunity (status + reviewer fields)
  rather than a separate audit table, since a single review step doesn't
  need its own history table yet.
- Premium "early access" is a time window, not a hard content split:
  every approved opportunity gets a `published_at` (when premium users can
  see it) and a `free_access_at` (published_at + EARLY_ACCESS_WINDOW, when
  free users can see it too). Query filters do the rest — no duplicate data.
"""

from datetime import datetime, timedelta
import enum
import uuid

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# How long free users wait after an opportunity is approved before they see it.
# Premium users see it immediately at approval. Adjust freely — it's read from
# here in one place (Opportunity.approve()) so the window is easy to tune.
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
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)

    # --- Premium status ------------------------------------------------
    # Kept as simple fields rather than a subscriptions table for now —
    # add PremiumSubscription (with payment references) later if/when
    # billing is wired up. is_premium_active() is the one method that
    # should be called everywhere else, so that later change is contained.
    is_premium = db.Column(db.Boolean, default=False, nullable=False)
    premium_expires_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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


# ---------------------------------------------------------------------------
# Opportunity categories (admin-manageable, not hard-coded)
# ---------------------------------------------------------------------------

class OpportunityCategory(db.Model):
    __tablename__ = "opportunity_categories"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slug = db.Column(db.String(50), unique=True, nullable=False)   # 'jobs', 'scholarships'
    name = db.Column(db.String(120), nullable=False)               # 'Jobs & Internships'
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

    opportunities = db.relationship("Opportunity", back_populates="category")


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

class Opportunity(db.Model):
    __tablename__ = "opportunities"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)

    posted_by_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(UUID(as_uuid=False), db.ForeignKey("opportunity_categories.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    organization = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200))                # nullable: remote/unspecified
    opportunity_url = db.Column(db.String(500))          # external application link
    application_deadline = db.Column(db.DateTime)

    # --- Moderation ------------------------------------------------------
    status = db.Column(db.Enum(OpportunityStatus), nullable=False, default=OpportunityStatus.PENDING)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_by_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"))
    reviewed_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)

    # --- Premium early access ---------------------------------------------
    published_at = db.Column(db.DateTime)      # set on approval; premium sees it now
    free_access_at = db.Column(db.DateTime)    # published_at + EARLY_ACCESS_WINDOW

    posted_by = db.relationship("User", back_populates="opportunities_posted", foreign_keys=[posted_by_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])
    category = db.relationship("OpportunityCategory", back_populates="opportunities")
    saved_by = db.relationship("SavedOpportunity", back_populates="opportunity", cascade="all, delete-orphan")

    def approve(self, admin_user: "User") -> None:
        """Admin approves a pending opportunity: goes live for premium users now,
        and for free users after EARLY_ACCESS_WINDOW."""
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


class SavedOpportunity(db.Model):
    """A user bookmarking an opportunity to revisit later."""
    __tablename__ = "saved_opportunities"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(UUID(as_uuid=False), db.ForeignKey("opportunities.id"), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="saved_opportunities")
    opportunity = db.relationship("Opportunity", back_populates="saved_by")

    __table_args__ = (
        db.UniqueConstraint("user_id", "opportunity_id", name="uq_saved_user_opportunity"),
    )