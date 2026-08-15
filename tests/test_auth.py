"""Integration tests for registration, login and access control."""
import re

from app.extensions import mail
from app.models import User


def _extract_link_token(body: str, path: str) -> str:
    match = re.search(rf"{re.escape(path)}/([^\s]+)", body)
    assert match, f"no {path}/<token> link found in mail body:\n{body}"
    return match.group(1)


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


# --- E-mail confirmation ----------------------------------------------------

def test_register_sends_confirmation_and_blocks_login_until_confirmed(client, db):
    with mail.record_messages() as outbox:
        client.post(
            "/auth/register",
            data={
                "username": "pending",
                "email": "pending@example.com",
                "password": "supersecret1",
                "privacy_consent": "y",
            },
            follow_redirects=True,
        )
    assert len(outbox) == 1
    assert outbox[0].recipients == ["pending@example.com"]
    assert User.query.filter_by(username="pending").first().email_confirmed is False

    # login rejected before confirmation
    client.post("/auth/login", data={"username": "pending", "password": "supersecret1"})
    assert client.get("/products/new").status_code == 302  # still anonymous

    token = _extract_link_token(outbox[0].body, "/auth/confirm")
    resp = client.get(f"/auth/confirm/{token}", follow_redirects=True)
    assert resp.status_code == 200
    assert User.query.filter_by(username="pending").first().email_confirmed is True

    # login succeeds after confirmation
    client.post("/auth/login", data={"username": "pending", "password": "supersecret1"})
    assert client.get("/products/new").status_code == 200


def test_confirm_email_rejects_invalid_token(client):
    resp = client.get("/auth/confirm/not-a-real-token", follow_redirects=True)
    assert resp.status_code == 200


def test_resend_confirmation_sends_mail_for_unconfirmed_user(client, db):
    u = User(username="unconfirmed", email="unconfirmed@example.com", privacy_consent=True)
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()

    with mail.record_messages() as outbox:
        resp = client.post("/auth/resend-confirmation", data={"email": "unconfirmed@example.com"}, follow_redirects=True)
    assert resp.status_code == 200
    assert len(outbox) == 1
    assert outbox[0].recipients == ["unconfirmed@example.com"]


def test_resend_confirmation_for_unknown_email_sends_no_mail(client):
    with mail.record_messages() as outbox:
        resp = client.post("/auth/resend-confirmation", data={"email": "nobody@example.com"}, follow_redirects=True)
    assert resp.status_code == 200
    assert len(outbox) == 0


# --- Password reset ----------------------------------------------------------

def test_password_reset_flow_sets_new_password(client, user, db):
    with mail.record_messages() as outbox:
        client.post("/auth/reset-password", data={"email": user.email}, follow_redirects=True)
    assert len(outbox) == 1
    assert outbox[0].recipients == [user.email]

    token = _extract_link_token(outbox[0].body, "/auth/reset-password")
    resp = client.post(f"/auth/reset-password/{token}", data={"password": "brandnewpassword1"}, follow_redirects=True)
    assert resp.status_code == 200
    assert db.session.get(User, user.id).check_password("brandnewpassword1")

    # old password no longer works, new one does
    client.post("/auth/login", data={"username": user.username, "password": "brandnewpassword1"})
    assert client.get("/products/new").status_code == 200


def test_password_reset_request_for_unknown_email_sends_no_mail(client):
    with mail.record_messages() as outbox:
        resp = client.post("/auth/reset-password", data={"email": "nobody@example.com"}, follow_redirects=True)
    assert resp.status_code == 200
    assert len(outbox) == 0


def test_reset_password_rejects_invalid_token(client):
    resp = client.get("/auth/reset-password/not-a-real-token", follow_redirects=True)
    assert resp.status_code == 200


# --- Admin test mail ----------------------------------------------------------

def test_admin_can_send_test_mail(client, admin):
    client.post("/auth/login", data={"username": "admin", "password": "adminpass123"})
    with mail.record_messages() as outbox:
        resp = client.post("/admin/mail/test", data={"recipient": "check@example.com"}, follow_redirects=True)
    assert resp.status_code == 200
    assert len(outbox) == 1
    assert outbox[0].recipients == ["check@example.com"]


def test_send_test_mail_requires_admin(client, user):
    client.post("/auth/login", data={"username": "tester", "password": "password123"})
    resp = client.post("/admin/mail/test", data={"recipient": "x@example.com"})
    assert resp.status_code == 403
