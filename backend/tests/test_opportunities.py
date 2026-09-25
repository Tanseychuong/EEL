from datetime import timedelta

import pytest
from django.utils import timezone

from apps.opportunities.models import Opportunity


@pytest.fixture
def pending_opportunity(db, user, category):
    return Opportunity.objects.create(
        posted_by=user, category=category, title="Pending Job", description="A job.",
    )


@pytest.mark.django_db
class TestSubmission:
    def test_authenticated_user_can_submit(self, api_client, user, category):
        api_client.force_authenticate(user=user)
        response = api_client.post("/api/opportunities/", {
            "title": "New Gig", "description": "desc", "category": category.id,
        })
        assert response.status_code == 201
        assert Opportunity.objects.get(title="New Gig").status == Opportunity.Status.PENDING

    def test_anonymous_cannot_submit(self, api_client, category):
        response = api_client.post("/api/opportunities/", {
            "title": "New Gig", "description": "desc", "category": category.id,
        })
        assert response.status_code in (401, 403)


@pytest.mark.django_db
class TestVisibility:
    """The most important behavior in the app — get this wrong and either
    free users get early access for free, or premium gets no benefit."""

    def test_pending_not_visible_in_list(self, api_client, pending_opportunity):
        response = api_client.get("/api/opportunities/")
        titles = [o["title"] for o in response.data["results"]]
        assert pending_opportunity.title not in titles

    def test_approved_not_yet_visible_to_free_user_in_window(self, api_client, admin_user, pending_opportunity, user):
        pending_opportunity.approve(admin_user)  # free_access_at defaults to now + 48h

        api_client.force_authenticate(user=user)
        response = api_client.get("/api/opportunities/")
        titles = [o["title"] for o in response.data["results"]]
        assert pending_opportunity.title not in titles

    def test_approved_visible_to_free_user_after_window(self, api_client, admin_user, pending_opportunity, user):
        pending_opportunity.approve(admin_user)
        pending_opportunity.free_access_at = timezone.now() - timedelta(hours=1)
        pending_opportunity.save()

        api_client.force_authenticate(user=user)
        response = api_client.get("/api/opportunities/")
        titles = [o["title"] for o in response.data["results"]]
        assert pending_opportunity.title in titles

    def test_approved_visible_immediately_to_premium_user(self, api_client, admin_user, pending_opportunity, premium_user):
        pending_opportunity.approve(admin_user)  # published_at = now

        api_client.force_authenticate(user=premium_user)
        response = api_client.get("/api/opportunities/")
        titles = [o["title"] for o in response.data["results"]]
        assert pending_opportunity.title in titles

    def test_owner_can_retrieve_own_pending_by_id(self, api_client, user, pending_opportunity):
        api_client.force_authenticate(user=user)
        response = api_client.get(f"/api/opportunities/{pending_opportunity.id}/")
        assert response.status_code == 200

    def test_other_user_cannot_retrieve_someone_elses_pending(self, api_client, premium_user, pending_opportunity):
        api_client.force_authenticate(user=premium_user)
        response = api_client.get(f"/api/opportunities/{pending_opportunity.id}/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestModeration:
    def test_regular_user_cannot_approve(self, api_client, user, pending_opportunity):
        api_client.force_authenticate(user=user)
        response = api_client.post(f"/api/opportunities/{pending_opportunity.id}/approve/")
        assert response.status_code == 403

    def test_admin_can_approve(self, api_client, admin_user, pending_opportunity):
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(f"/api/opportunities/{pending_opportunity.id}/approve/")
        assert response.status_code == 200
        pending_opportunity.refresh_from_db()
        assert pending_opportunity.status == Opportunity.Status.APPROVED

    def test_moderator_can_approve(self, api_client, moderator_user, pending_opportunity):
        """The whole point of the Groups/permission setup — a non-admin,
        non-superuser account can still verify opportunities."""
        api_client.force_authenticate(user=moderator_user)
        response = api_client.post(f"/api/opportunities/{pending_opportunity.id}/approve/")
        assert response.status_code == 200

    def test_reject_requires_reason(self, api_client, admin_user, pending_opportunity):
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(f"/api/opportunities/{pending_opportunity.id}/reject/", {})
        assert response.status_code == 400

    def test_reject_sets_status_and_reason(self, api_client, admin_user, pending_opportunity):
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(f"/api/opportunities/{pending_opportunity.id}/reject/", {"reason": "Not legit."})
        assert response.status_code == 200
        pending_opportunity.refresh_from_db()
        assert pending_opportunity.status == Opportunity.Status.REJECTED
        assert pending_opportunity.rejection_reason == "Not legit."


@pytest.mark.django_db
class TestSaving:
    def test_save_and_list_saved(self, api_client, user, admin_user, pending_opportunity):
        pending_opportunity.approve(admin_user)
        pending_opportunity.free_access_at = timezone.now() - timedelta(hours=1)
        pending_opportunity.save()

        api_client.force_authenticate(user=user)
        save_response = api_client.post(f"/api/opportunities/{pending_opportunity.id}/save/")
        assert save_response.status_code == 201

        saved_response = api_client.get("/api/opportunities/saved/")
        assert saved_response.data["results"][0]["opportunity"]["title"] == pending_opportunity.title

    def test_unsave_removes_it(self, api_client, user, admin_user, pending_opportunity):
        pending_opportunity.approve(admin_user)
        api_client.force_authenticate(user=user)
        api_client.post(f"/api/opportunities/{pending_opportunity.id}/save/")

        response = api_client.delete(f"/api/opportunities/{pending_opportunity.id}/unsave/")
        assert response.status_code == 204

        saved_response = api_client.get("/api/opportunities/saved/")
        assert saved_response.data["count"] == 0
