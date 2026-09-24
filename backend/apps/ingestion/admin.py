from django.contrib import admin

from .models import FetchSource, FetchLog
from .services import fetch_source


@admin.action(description="Fetch now")
def fetch_now(modeladmin, request, queryset):
    for source in queryset:
        log = fetch_source(source)
        modeladmin.message_user(
            request,
            f"{source.name}: {log.status} — found {log.items_found}, created {log.items_created}"
            + (f" — {log.error_message}" if log.error_message else ""),
        )


@admin.register(FetchSource)
class FetchSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "connector_type", "category", "is_active", "last_fetched_at")
    list_filter = ("connector_type", "is_active", "category")
    search_fields = ("name", "url")
    actions = [fetch_now]


@admin.register(FetchLog)
class FetchLogAdmin(admin.ModelAdmin):
    list_display = ("source", "status", "items_found", "items_created", "started_at", "finished_at")
    list_filter = ("status", "source")
    readonly_fields = [f.name for f in FetchLog._meta.fields]  # this is a history record, never hand-edited

    def has_add_permission(self, request):
        return False  # logs are only ever created by fetch_source(), never by hand
