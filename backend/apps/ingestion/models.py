"""
Tracks *where* opportunities get auto-fetched from and *what happened* each
time a fetch ran. Deliberately separate from apps.opportunities — adding a
new source later means adding one FetchSource row + one connector class,
never touching the core Opportunity model or moderation logic.
"""

from django.db import models


class FetchSource(models.Model):
    class ConnectorType(models.TextChoices):
        RSS = "rss", "RSS / Atom feed"
        # Add more as real sources are identified, e.g.:
        # JSON_API = "json_api", "JSON API"
        # HTML_SCRAPE = "html_scrape", "HTML scrape"

    name = models.CharField(max_length=120)
    connector_type = models.CharField(max_length=30, choices=ConnectorType.choices)
    url = models.URLField(max_length=500)

    # Every fetched opportunity needs a category — this is the default
    # applied to everything this source produces, since most feeds don't
    # self-describe into our category scheme.
    category = models.ForeignKey(
        "opportunities.OpportunityCategory", on_delete=models.PROTECT, related_name="fetch_sources"
    )

    is_active = models.BooleanField(default=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["is_active"])]

    def __str__(self):
        return self.name


class FetchLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial (some items failed)"
        FAILURE = "failure", "Failure"

    source = models.ForeignKey(FetchSource, on_delete=models.CASCADE, related_name="logs")
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices)
    items_found = models.PositiveIntegerField(default=0)
    items_created = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["source", "-started_at"])]

    def __str__(self):
        return f"{self.source.name} @ {self.started_at:%Y-%m-%d %H:%M} ({self.status})"
