"""
EEL — Opportunity Portal
Database models (Flask-SQLAlchemy / PostgreSQL).


- Any signed-in user can submit an opportunity; it stays PENDING until an
  admin approves it (moderation queue).
- Premium status lives on the User (denormalized `is_premium` flag kept in
  sync by a Subscription record) and drives EARLY/EXCLUSIVE ACCESS:
    * every approved opportunity gets a `public_release_at` timestamp,
      `early_access_hours` after approval — premium users can see it the
      moment it's approved, everyone else waits until that timestamp.
    * an opportunity can also be marked `premium_only=True` to stay
      exclusive to premium users indefinitely.
  `Opportunity.visible_to()` encodes that rule in one place so every
  endpoint checks visibility the same way.
"""

from datetime import datetime, timedelta
import enum
import uuid

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def gen_uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"


class OpportunityType(enum.Enum):
    JOB = "job"
    INTERNSHIP = "internship"
    SCHOLARSHIP = "scholarship"
    GRANT = "grant"
    FELLOWSHIP = "fellowship"
    COMPETITION = "competition"
    VOLUNTEER = "volunteer"
    OTHER = "other"


class OpportunityStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SubscriptionPlan(enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELED = "canceled"


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

    # Denormalized for fast checks (e.g. `if user.is_premium`) — kept in
    # sync whenever a Subscription is created/renewed/expired.
    is_premium = db.Column(db.Boolean, nullable=False, default=False)
    premium_expires_at = db.Column(db.DateTime)  # null for LIFETIME plans

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    opportunities_posted = db.relationship(
        "Opportunity", back_populates="poster",
        foreign_keys="Opportunity.poster_id", cascade="all, delete-orphan"
    )
    approvals_made = db.relationship(
        "Opportunity", back_populates="approver",
        foreign_keys="Opportunity.approved_by"
    )
    saved_opportunities = db.relationship(
        "SavedOpportunity", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions = db.relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def refresh_premium_flag(self) -> None:
        """Call after touching a subscription to keep is_premium accurate."""
        active = (
            db.session.query(Subscription)
            .filter_by(user_id=self.id, status=SubscriptionStatus.ACTIVE)
            .filter(
                db.or_(
                    Subscription.expires_at.is_(None),          # lifetime
                    Subscription.expires_at > datetime.utcnow(),
                )
            )
            .first()
        )
        self.is_premium = active is not None
        self.premium_expires_at = active.expires_at if active else None


# ---------------------------------------------------------------------------
# Subscriptions (drive premium status)
# ---------------------------------------------------------------------------

class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False)
    plan = db.Column(db.Enum(SubscriptionPlan), nullable=False)
    status = db.Column(db.Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.ACTIVE)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)  # null for LIFETIME
    payment_reference = db.Column(db.String(255))  # e.g. Stripe/Paystack charge id

    user = db.relationship("User", back_populates="subscriptions")


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------

class Opportunity(db.Model):
    __tablename__ = "opportunities"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)

    poster_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    organization = db.Column(db.String(200))
    opportunity_type = db.Column(db.Enum(OpportunityType), nullable=False)
    location = db.Column(db.String(200))
    is_remote = db.Column(db.Boolean, default=False)
    deadline = db.Column(db.Date)
    external_url = db.Column(db.String(500))

    # --- Moderation -----------------------------------------------------
    status = db.Column(db.Enum(OpportunityStatus), nullable=False, default=OpportunityStatus.PENDING)
    rejection_reason = db.Column(db.Text)
    approved_by = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"))
    approved_at = db.Column(db.DateTime)

    # --- Premium access ---------------------------------------------------
    premium_only = db.Column(db.Boolean, nullable=False, default=False)
    early_access_hours = db.Column(db.Integer, nullable=False, default=24)
    public_release_at = db.Column(db.DateTime)  # set when approved

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    poster = db.relationship("User", back_populates="opportunities_posted", foreign_keys=[poster_id])
    approver = db.relationship("User", back_populates="approvals_made", foreign_keys=[approved_by])
    saves = db.relationship("SavedOpportunity", back_populates="opportunity", cascade="all, delete-orphan")
    tags = db.relationship("Tag", secondary="opportunity_tags", back_populates="opportunities")

    # -- Moderation actions -------------------------------------------------
    def approve(self, admin: "User") -> None:
        self.status = OpportunityStatus.APPROVED
        self.approved_by = admin.id
        self.approved_at = datetime.utcnow()
        self.public_release_at = self.approved_at + timedelta(hours=self.early_access_hours)

    def reject(self, admin: "User", reason: str = "") -> None:
        self.status = OpportunityStatus.REJECTED
        self.approved_by = admin.id
        self.approved_at = datetime.utcnow()
        self.rejection_reason = reason

    # -- Visibility rule: the one place premium access is decided -----------
    def visible_to(self, user: "User" = None, now: datetime = None) -> bool:
        if self.status != OpportunityStatus.APPROVED:
            return False
        now = now or datetime.utcnow()
        if user is not None and user.is_premium:
            return True
        if self.premium_only:
            return False
        return self.public_release_at is not None and now >= self.public_release_at


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(80), unique=True, nullable=False)

    opportunities = db.relationship("Opportunity", secondary="opportunity_tags", back_populates="tags")


opportunity_tags = db.Table(
    "opportunity_tags",
    db.Column("opportunity_id", UUID(as_uuid=False), db.ForeignKey("opportunities.id"), primary_key=True),
    db.Column("tag_id", UUID(as_uuid=False), db.ForeignKey("tags.id"), primary_key=True),
)


class SavedOpportunity(db.Model):
    """A user bookmarking an opportunity for later."""
    __tablename__ = "saved_opportunities"

    id = db.Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = db.Column(UUID(as_uuid=False), db.ForeignKey("users.id"), nullable=False)
    opportunity_id = db.Column(UUID(as_uuid=False), db.ForeignKey("opportunities.id"), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="saved_opportunities")
    opportunity = db.relationship("Opportunity", back_populates="saves")

    __table_args__ = (
        db.UniqueConstraint("user_id", "opportunity_id", name="uq_saved_user_opportunity"),
    )