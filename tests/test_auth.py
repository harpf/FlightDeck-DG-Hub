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


def test_admin_can_deactivate_user(client, admin, user, db):
    client.post("/auth/login", data={"username": "admin", "password": "adminpass123"})
    resp = client.post(f"/admin/users/{user.id}/toggle-active", follow_redirects=True)
    assert resp.status_code == 200
    assert db.session.get(User, user.id).is_active is False
    # toggling again re-activates
    client.post(f"/admin/users/{user.id}/toggle-active")
    assert db.session.get(User, user.id).is_active is True


def test_admin_cannot_deactivate_self(client, admin, db):
    client.post("/auth/login", data={"username": "admin", "password": "adminpass123"})
    client.post(f"/admin/users/{admin.id}/toggle-active", follow_redirects=True)
    assert db.session.get(User, admin.id).is_active is True


def test_deactivated_user_cannot_login(client, user, db):
    user.is_active = False
    db.session.commit()
    resp = client.post(
        "/auth/login",
        data={"username": "tester", "password": "password123"},
        follow_redirects=True,
    )
    assert "deaktiviert".encode() in resp.data
    assert client.get("/products/new").status_code == 302  # not logged in


def test_active_session_ends_when_deactivated(client, user, db):
    client.post("/auth/login", data={"username": "tester", "password": "password123"})
    assert client.get("/products/new").status_code == 200  # logged in
    user.is_active = False
    db.session.commit()
    resp = client.get("/products/new")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_toggle_user_requires_admin(client, user, admin):
    client.post("/auth/login", data={"username": "tester", "password": "password123"})
    resp = client.post(f"/admin/users/{admin.id}/toggle-active")
    assert resp.status_code == 403


def test_create_product_requires_login(client):
    resp = client.get("/products/new")
    # Flask-Login redirects anonymous users to the login page
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
