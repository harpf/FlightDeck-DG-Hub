import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "mysql+pymysql://flightdeck:flightdeck@db:3306/flightdeck")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True

    BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")

    # Mail (Postfix container on the internal Docker network, direct-send, no auth/TLS needed)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "postfix")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "25"))
    MAIL_USE_TLS = False
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "no-reply@flightdeck.local")

    # Token lifetimes (seconds) for e-mail confirmation / password reset links
    CONFIRM_TOKEN_MAX_AGE = 60 * 60 * 24  # 24h
    RESET_TOKEN_MAX_AGE = 60 * 60  # 1h


class TestingConfig(Config):
    """Config for the automated test suite.

    Uses an in-memory SQLite database so the integration tests run without a
    MariaDB server. The ORM models are database-agnostic, so this exercises the
    same SQLAlchemy code paths used in production against MariaDB.
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
    MAIL_SUPPRESS_SEND = True
