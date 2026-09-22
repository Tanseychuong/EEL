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

from apps.extensions import db
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
