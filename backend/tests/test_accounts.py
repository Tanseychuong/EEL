import pytest


@pytest.mark.django_db
class TestRegistration:
    def test_register_creates_user(self, api_client):
        response = api_client.post("/api/auth/register/", {
            "name": "New User", "email": "new@example.com", "password": "StrongPass123!",
        })
        assert response.status_code == 201
        assert response.data["email"] == "new@example.com"

    def test_register_rejects_weak_password(self, api_client):
        response = api_client.post("/api/auth/register/", {
            "name": "New User", "email": "weak@example.com", "password": "123",
        })
        assert response.status_code == 400

    def test_register_rejects_duplicate_email(self, api_client, user):
        response = api_client.post("/api/auth/register/", {
            "name": "Dupe", "email": user.email, "password": "StrongPass123!",
        })
        assert response.status_code == 400


@pytest.mark.django_db
class TestLogin:
    def test_login_returns_tokens(self, api_client, user):
        response = api_client.post("/api/auth/login/", {"email": user.email, "password": "testpass123"})
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password_fails(self, api_client, user):
        response = api_client.post("/api/auth/login/", {"email": user.email, "password": "wrong"})
        assert response.status_code == 401


@pytest.mark.django_db
class TestMe:
    def test_me_requires_auth(self, api_client):
        response = api_client.get("/api/auth/me/")
        assert response.status_code == 401

    def test_me_returns_profile(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/auth/me/")
        assert response.status_code == 200
        assert response.data["email"] == user.email
        assert response.data["role"] == "user"

    def test_me_shows_premium_active(self, api_client, premium_user):
        api_client.force_authenticate(user=premium_user)
        response = api_client.get("/api/auth/me/")
        assert response.data["is_premium_active"] is True

    def test_me_shows_admin_role(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/auth/me/")
        assert response.data["role"] == "admin"

    def test_me_shows_moderator_role(self, api_client, moderator_user):
        api_client.force_authenticate(user=moderator_user)
        response = api_client.get("/api/auth/me/")
        assert response.data["role"] == "moderator"
