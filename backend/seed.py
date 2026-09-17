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
