from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/opportunities/", include("apps.opportunities.urls")),
    path("api/ingestion/", include("apps.ingestion.urls")),
]
