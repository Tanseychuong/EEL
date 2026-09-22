"""
Django's built-in UserCreationForm/UserChangeForm assume a `username`
field. Since our User uses email as the login field instead, the admin
needs these overrides or creating/editing a user from /admin/ breaks.
"""

from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.contrib.auth.forms import UserChangeForm as BaseUserChangeForm

from .models import User


class UserCreationForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ("email", "name")


class UserChangeForm(BaseUserChangeForm):
    class Meta(BaseUserChangeForm.Meta):
        model = User
        fields = ("email", "name", "is_premium", "premium_expires_at")
