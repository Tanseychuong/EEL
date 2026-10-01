from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
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

if settings.DEBUG:
    # Local disk serving for dev only — a real deploy needs a proper media
    # storage backend (see the note on MEDIA_ROOT in settings.py).
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
