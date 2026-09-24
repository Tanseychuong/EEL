"""
Run via:
    python manage.py fetch_opportunities
    python manage.py fetch_opportunities --source "Some Source Name"

Meant to be cron-scheduled (or run manually) — this is the automated half
of ingestion; the admin's "Fetch now" action (apps/ingestion/admin.py)
calls the same services.fetch_source() for the manual/on-demand half.
"""

from django.core.management.base import BaseCommand

from apps.ingestion.models import FetchSource
from apps.ingestion.services import fetch_source


class Command(BaseCommand):
    help = "Fetch opportunities from all active FetchSources (or one, with --source)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", type=str, default=None,
            help="Only fetch from the source with this exact name",
        )

    def handle(self, *args, **options):
        sources = FetchSource.objects.filter(is_active=True)
        if options["source"]:
            sources = sources.filter(name=options["source"])

        if not sources.exists():
            self.stdout.write(self.style.WARNING("No active sources matched."))
            return

        for source in sources:
            log = fetch_source(source)
            style = self.style.SUCCESS if log.status == "success" else (
                self.style.WARNING if log.status == "partial" else self.style.ERROR
            )
            self.stdout.write(style(
                f"{source.name}: {log.status} — found {log.items_found}, created {log.items_created}"
                + (f" — {log.error_message}" if log.error_message else "")
            ))
