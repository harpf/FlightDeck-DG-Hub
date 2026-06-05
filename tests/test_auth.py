"""Integration tests for registration, login and access control."""
from app.models import User


def test_register_creates_user(client, db):
    resp = client.post(
        "/auth/register",
        data={
            "username": "newuser",
            "email": "new@example.com",
            "password": "supersecret1",
            "privacy_consent": "y",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert User.query.filter_by(username="newuser").count() == 1


def test_register_rejects_duplicate_username(client, user):
    resp = client.post(
        "/auth/register",
        data={
            "username": "tester",  # already exists via the `user` fixture
            "email": "other@example.com",
            "password": "supersecret1",
            "privacy_consent": "y",
        },
        follow_redirects=True,
    )
    # The app re-renders the form and does not create a second account
    assert User.query.filter_by(username="tester").count() == 1


def test_register_requires_privacy_consent(client, db):
    resp = client.post(
        "/auth/register",
        data={"username": "noconsent", "email": "nc@example.com", "password": "supersecret1"},
        follow_redirects=True,
    )
    assert User.query.filter_by(username="noconsent").count() == 0


def test_login_succeeds_with_valid_credentials(client, user):
    resp = client.post(
        "/auth/login",
        data={"username": "tester", "password": "password123"},
        follow_redirects=True,
    )
    assert resp.status_code == 200


def test_login_fails_with_wrong_password(client, user):
    resp = client.post(
        "/auth/login",
        data={"username": "tester", "password": "wrongpassword"},
        follow_redirects=True,
    )
    assert "Ungültige Zugangsdaten".encode() in resp.data


def test_admin_dashboard_lists_users(client, admin, user):
    client.post("/auth/login", data={"username": "admin", "password": "adminpass123"})
    resp = client.get("/admin/")
    assert resp.status_code == 200
    assert b"Registrierte Benutzer" in resp.data
    assert b"tester@example.com" in resp.data  # the `user` fixture's email


def test_admin_dashboard_forbidden_for_normal_user(client, user):
    client.post("/auth/login", data={"username": "tester", "password": "password123"})
    resp = client.get("/admin/")
    assert resp.status_code == 403


def test_create_product_requires_login(client):
    resp = client.get("/products/new")
    # Flask-Login redirects anonymous users to the login page
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
