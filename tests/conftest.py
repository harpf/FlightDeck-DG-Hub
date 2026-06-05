"""Shared pytest fixtures for the FlightDeck DG Hub test suite.

The integration tests build a real Flask app via the application factory using
``TestingConfig`` (in-memory SQLite + CSRF disabled), create the schema fresh
for every test, and tear it down afterwards so tests stay isolated.
"""
import pytest

from app import create_app
from app.extensions import db as _db
from app.models import ApiToken, Product, User
from config import TestingConfig


@pytest.fixture()
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def user(db):
    """A normal registered user."""
    u = User(username="tester", email="tester@example.com", privacy_consent=True)
    u.set_password("password123")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture()
def admin(db):
    a = User(username="admin", email="admin@example.com", is_admin=True, privacy_consent=True)
    a.set_password("adminpass123")
    db.session.add(a)
    db.session.commit()
    return a


@pytest.fixture()
def product(db):
    p = Product(name="Destroyer", manufacturer="Innova", category="Disc", disc_type="Distance Driver", speed=12, glide=5, turn=-1, fade=3)
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture()
def api_token(db, admin):
    """Creates an active API token and returns the plaintext value for headers."""
    token = ApiToken(name="test-token", created_by_id=admin.id, token_hash="placeholder")
    db.session.add(token)
    db.session.flush()
    secret = ApiToken.generate_secret()
    token.set_secret(secret)
    db.session.commit()
    return ApiToken.build_plaintext_token(token.id, secret)
