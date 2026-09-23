"""
Core domain models for the opportunity portal.

Both user-submitted and auto-fetched opportunities are rows in this same
Opportunity table (source_type tells them apart) — one moderation queue,
one set of visibility rules, regardless of where a listing came from.

The can_verify_opportunity permission (Meta.permissions below) is what
lets a non-admin user approve/reject — granted via a "Moderators" Group in
Django admin, not a field on User. See docs/opportunities.md.
"""

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

EARLY_ACCESS_WINDOW = timedelta(hours=getattr(settings, "EARLY_ACCESS_HOURS", 48))


class OpportunityCategory(models.Model):
    """Admin-manageable, not an enum, so new categories don't need a code
    change — same reasoning as the Flask version."""

    slug = models.SlugField(unique=True)          # 'jobs', 'scholarships'
    name = models.CharField(max_length=120)         # 'Jobs & Internships'
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "opportunity categories"
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return self.name


class Opportunity(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class SourceType(models.TextChoices):
        SUBMITTED = "submitted", "User submitted"
        FETCHED = "fetched", "Auto-fetched"

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="opportunities_posted", null=True, blank=True,
        # null=True: a FETCHED opportunity has no human poster
    )
    category = models.ForeignKey(
        OpportunityCategory, on_delete=models.PROTECT, related_name="opportunities"
    )

    title = models.CharField(max_length=200)
    organization = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    location = models.CharField(max_length=200, blank=True)
    opportunity_url = models.URLField(max_length=500, blank=True)
    application_deadline = models.DateTimeField(null=True, blank=True)

    source_type = models.CharField(
        max_length=20, choices=SourceType.choices, default=SourceType.SUBMITTED
    )
    # Set only for FETCHED opportunities — nullable FK to avoid a circular
    # import with the ingestion app (opportunities shouldn't have to know
    # ingestion's internals beyond "which source did this come from").
    fetch_source = models.ForeignKey(
        "ingestion.FetchSource", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="opportunities",
    )

    # --- Moderation ------------------------------------------------------
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="opportunities_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # --- Premium early access ---------------------------------------------
    published_at = models.DateTimeField(null=True, blank=True)
    free_access_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "opportunities"
        permissions = [
            ("can_verify_opportunity", "Can approve or reject opportunities"),
        ]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["status", "free_access_at"]),
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["application_deadline"]),
        ]

    def __str__(self):
        return self.title

    def approve(self, reviewer) -> None:
        now = timezone.now()
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = now
        self.published_at = now
        self.free_access_at = now + EARLY_ACCESS_WINDOW
        self.save()

    def reject(self, reviewer, reason: str) -> None:
        self.status = self.Status.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save()

    def is_visible_to(self, user) -> bool:
        if self.status != self.Status.APPROVED:
            return False
        now = timezone.now()
        if user is not None and user.is_authenticated and user.is_premium_active():
            return self.published_at is not None and self.published_at <= now
        return self.free_access_at is not None and self.free_access_at <= now

    @classmethod
    def visible_to(cls, user):
        """Query-level visibility filter — stays index-backed instead of
        loading every row to check it in Python. Use this in every list
        view rather than filtering in a loop."""
        now = timezone.now()
        base = cls.objects.filter(status=cls.Status.APPROVED)
        if user is not None and getattr(user, "is_authenticated", False) and user.is_premium_active():
            return base.filter(published_at__lte=now)
        return base.filter(free_access_at__lte=now)


class SavedOpportunity(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_opportunities"
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="saved_by"
    )
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "opportunity"], name="uq_saved_user_opportunity")
        ]

    def __str__(self):
        return f"{self.user} saved {self.opportunity}"
