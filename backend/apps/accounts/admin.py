"""
Registers User with the Django admin. This IS the admin's user-management
UI — including where you'll assign the "Moderators" group to specific
users, once that group exists (created in opportunities/models.py's
migration or manually in /admin/auth/group/).
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserCreationForm, UserChangeForm
from .models import User


class UserAdmin(BaseUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User

    ordering = ("email",)
    list_display = ("email", "name", "is_staff", "is_superuser", "is_premium", "created_at")
    list_filter = ("is_staff", "is_superuser", "is_premium", "is_active")
    search_fields = ("email", "name")
    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name",)}),
        ("Premium", {"fields": ("is_premium", "premium_expires_at")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active", "is_staff", "is_superuser",
                    "groups", "user_permissions",   # <- assign "Moderators" group here
                ),
            },
        ),
        ("Important dates", {"fields": ("created_at",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2"),
            },
        ),
    )


admin.site.register(User, UserAdmin)
