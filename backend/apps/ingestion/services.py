"""
The actual fetch-one-source logic, kept out of both the management command
and admin.py so there's exactly one implementation of "run a source and
record what happened" — called from a cron-scheduled command and from a
moderator clicking "Fetch now" in /admin/ alike.
"""

from django.utils import timezone

from apps.opportunities.models import Opportunity

from .connectors import get_connector_class
from .models import FetchLog


def fetch_source(source) -> FetchLog:
    started_at = timezone.now()
    items_found = 0
    items_created = 0
    error_message = ""
    log_status = FetchLog.Status.SUCCESS

    try:
        connector_cls = get_connector_class(source.connector_type)
        connector = connector_cls(source)
        items = connector.fetch()
        items_found = len(items)

        for item in items:
            url = item.get("opportunity_url", "")
            # De-dupe on URL — a re-fetch of the same feed shouldn't create
            # duplicate PENDING opportunities every time it runs.
            if url and Opportunity.objects.filter(opportunity_url=url).exists():
                continue

            Opportunity.objects.create(
                title=item["title"],
                description=item.get("description", ""),
                organization=item.get("organization", source.name),
                location=item.get("location", ""),
                opportunity_url=url,
                application_deadline=item.get("application_deadline"),
                category=source.category,
                source_type=Opportunity.SourceType.FETCHED,
                status=Opportunity.Status.PENDING,
                fetch_source=source,
            )
            items_created += 1

        if items_found and not items_created:
            log_status = FetchLog.Status.PARTIAL  # feed had items, all were dupes — worth knowing, not an error

    except Exception as exc:  # noqa: BLE001 — genuinely want to catch+log anything here
        log_status = FetchLog.Status.FAILURE
        error_message = str(exc)

    finally:
        source.last_fetched_at = timezone.now()
        source.save(update_fields=["last_fetched_at"])

    return FetchLog.objects.create(
        source=source,
        started_at=started_at,
        finished_at=timezone.now(),
        status=log_status,
        items_found=items_found,
        items_created=items_created,
        error_message=error_message,
    )
