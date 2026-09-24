"""
Ingestion is primarily an admin-panel concern (manage sources, click
"Fetch now", read logs — all in apps/ingestion/admin.py). This one
read-only endpoint exists for a future ops dashboard; there's
intentionally no public API surface for ingestion beyond it.
"""

from django.urls import path
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FetchLog


class RecentFetchLogsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        logs = FetchLog.objects.select_related("source").all()[:50]
        data = [
            {
                "source": log.source.name,
                "status": log.status,
                "items_found": log.items_found,
                "items_created": log.items_created,
                "started_at": log.started_at,
                "finished_at": log.finished_at,
                "error_message": log.error_message,
            }
            for log in logs
        ]
        return Response(data)


urlpatterns = [
    path("logs/", RecentFetchLogsView.as_view(), name="ingestion-logs"),
]
