"""
Business logic kept out of views.py so it's testable on its own and
reusable — e.g. the same approve()/reject() path is used whether the
action comes from the DRF API or (in admin.py) from the Django admin's
bulk actions.
"""

from .models import Opportunity


def submit_opportunity(user, validated_data) -> Opportunity:
    """A user submits a new opportunity — always starts PENDING regardless
    of who's submitting, admins included, since even an admin's submission
    should go through the same visible moderation trail."""
    return Opportunity.objects.create(
        posted_by=user,
        source_type=Opportunity.SourceType.SUBMITTED,
        status=Opportunity.Status.PENDING,
        **validated_data,
    )


def approve_opportunity(opportunity: Opportunity, reviewer) -> Opportunity:
    opportunity.approve(reviewer)
    return opportunity


def reject_opportunity(opportunity: Opportunity, reviewer, reason: str) -> Opportunity:
    opportunity.reject(reviewer, reason)
    return opportunity


def list_visible_opportunities(user, category_slug: str | None = None):
    """The one place list endpoints get their queryset from — applies the
    premium/free visibility rule via Opportunity.visible_to(), then an
    optional category filter on top."""
    queryset = Opportunity.visible_to(user).select_related("category", "posted_by")
    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)
    return queryset.order_by("-published_at")
