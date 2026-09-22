"""
Custom User model for the EEL opportunity portal.

Uses Django's AbstractBaseUser + PermissionsMixin rather than extending the
default User, so email is the login field (no separate username) and we
keep full control over what fields exist — same reasoning as the Flask
User model, just Django's idioms.

Moderator privilege is deliberately NOT a field here — it's a Django
permission (opportunities.can_verify_opportunity) granted via a
"Moderators" Group, assignable from the Django admin's Groups UI with no
custom code. See apps/opportunities/models.py's Meta.permissions.
"""

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)

    # is_staff/is_superuser come from PermissionsMixin and control Django
    # admin access + full permissions — is_staff is what makes someone able
    # to log into /admin/ at all (moderators need this; is_superuser is the
    # "admin" tier from the original plan).
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # Premium status — same design as the Flask version. is_premium_active()
    # is the one method every view/permission check should call.
    is_premium = models.BooleanField(default=False)
    premium_expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        indexes = [
            models.Index(fields=["is_premium"]),
        ]

    def __str__(self):
        return self.email

    def is_premium_active(self) -> bool:
        """The single source of truth for 'does this user get early access'."""
        if not self.is_premium:
            return False
        if self.premium_expires_at is None:
            return True  # no expiry set = indefinite premium (e.g. admin-granted)
        return self.premium_expires_at > timezone.now()

    def is_moderator(self) -> bool:
        """True for superusers too, so admins never need the explicit
        permission on top of is_superuser."""
        return self.is_superuser or self.has_perm("opportunities.can_verify_opportunity")