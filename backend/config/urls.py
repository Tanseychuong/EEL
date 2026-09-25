from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),

    path("api/auth/", include("apps.accounts.urls")),
    path("api/opportunities/", include("apps.opportunities.urls")),
    path("api/ingestion/", include("apps.ingestion.urls")),
]
