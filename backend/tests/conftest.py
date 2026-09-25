"""
Shared fixtures. One user fixture per access tier (free/premium/moderator/
admin) so tests read as "given a <tier> user" rather than constructing
users inline everywhere — and so a change to how a tier is granted
(e.g. premium expiry logic) only needs updating here.
"""

import pytest
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.opportunities.models import OpportunityCategory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def category(db):
    return OpportunityCategory.objects.create(slug="jobs", name="Jobs & Internships")


@pytest.fixture
def user(db):
    return User.objects.create_user(email="user@example.com", name="Test User", password="testpass123")


@pytest.fixture
def premium_user(db):
    return User.objects.create_user(
        email="premium@example.com", name="Premium User",
        password="testpass123", is_premium=True,
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="admin@example.com", name="Admin", password="testpass123")


@pytest.fixture
def moderator_user(db):
    user = User.objects.create_user(
        email="mod@example.com", name="Moderator", password="testpass123", is_staff=True,
    )
    permission = Permission.objects.get(codename="can_verify_opportunity")
    user.user_permissions.add(permission)
    return user
