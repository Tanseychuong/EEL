"""
This admin interface IS the moderation queue — the whole reason we chose
Django. Filter by status=pending, select rows, "Approve selected" /
"Reject selected" — no custom frontend needed for moderators to work from
day one. A real admin UI can be built later without this ever blocking
launch.
"""

from django.contrib import admin, messages

from .models import Opportunity, OpportunityCategory, SavedOpportunity


@admin.register(OpportunityCategory)
class OpportunityCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.action(description="Approve selected opportunities")
def approve_opportunities(modeladmin, request, queryset):
    if not request.user.has_perm("opportunities.can_verify_opportunity"):
        modeladmin.message_user(request, "You don't have permission to verify opportunities.", level=messages.ERROR)
        return
    count = 0
    for opportunity in queryset:
        opportunity.approve(reviewer=request.user)
        count += 1
    modeladmin.message_user(request, f"Approved {count} opportunit{'y' if count == 1 else 'ies'}.")


@admin.action(description="Reject selected opportunities")
def reject_opportunities(modeladmin, request, queryset):
    if not request.user.has_perm("opportunities.can_verify_opportunity"):
        modeladmin.message_user(request, "You don't have permission to verify opportunities.", level=messages.ERROR)
        return
    count = queryset.update(
        status=Opportunity.Status.REJECTED,
        reviewed_by=request.user,
        rejection_reason="Rejected in bulk from the admin queue.",
    )
    modeladmin.message_user(request, f"Rejected {count} opportunit{'y' if count == 1 else 'ies'}.")


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = (
        "title", "category", "status", "source_type",
        "posted_by", "submitted_at", "application_deadline",
    )
    list_filter = ("status", "source_type", "category")
    search_fields = ("title", "organization", "description")
    readonly_fields = (
        "submitted_at", "reviewed_by", "reviewed_at",
        "published_at", "free_access_at",
    )
    actions = [approve_opportunities, reject_opportunities]

    fieldsets = (
        (None, {"fields": ("title", "organization", "category", "description", "location", "opportunity_url", "application_deadline")}),
        ("Source", {"fields": ("posted_by", "source_type", "fetch_source")}),
        ("Moderation", {"fields": ("status", "submitted_at", "reviewed_by", "reviewed_at", "rejection_reason")}),
        ("Premium early access", {"fields": ("published_at", "free_access_at")}),
    )

    def get_queryset(self, request):
        # Moderators only need to see this at all if they can act on it —
        # everyone with is_staff can still view, but the actions above
        # enforce the actual permission check.
        return super().get_queryset(request).select_related("category", "posted_by")


@admin.register(SavedOpportunity)
class SavedOpportunityAdmin(admin.ModelAdmin):
    list_display = ("user", "opportunity", "saved_at")
    search_fields = ("user__email", "opportunity__title")
