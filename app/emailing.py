"""Outbound e-mail: confirmation/reset tokens and message sending via the Postfix relay."""
import logging

from flask import current_app, url_for
from flask_mail import Message
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.extensions import mail

logger = logging.getLogger(__name__)

_CONFIRM_SALT = "email-confirm"
_RESET_SALT = "password-reset"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def _verify(token: str, salt: str, max_age: int) -> str | None:
    try:
        return _serializer().loads(token, salt=salt, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


def generate_confirm_token(user) -> str:
    return _serializer().dumps(user.email, salt=_CONFIRM_SALT)


def verify_confirm_token(token: str) -> str | None:
    """Return the e-mail address encoded in the token, or None if invalid/expired."""
    return _verify(token, _CONFIRM_SALT, current_app.config["CONFIRM_TOKEN_MAX_AGE"])


def generate_reset_token(user) -> str:
    return _serializer().dumps(user.email, salt=_RESET_SALT)


def verify_reset_token(token: str) -> str | None:
    """Return the e-mail address encoded in the token, or None if invalid/expired."""
    return _verify(token, _RESET_SALT, current_app.config["RESET_TOKEN_MAX_AGE"])


def _send(subject: str, recipient: str, body: str) -> bool:
    """Send a message; return True on success, log and return False on failure.

    Mail infrastructure hiccups (Postfix container unreachable, MX lookup
    failure, ...) must not turn the user-facing request that triggered the
    send into a 500.
    """
    try:
        mail.send(Message(subject=subject, recipients=[recipient], body=body))
        return True
    except Exception:
        logger.exception("Failed to send mail to %s", recipient)
        return False


def send_confirmation_email(user) -> bool:
    token = generate_confirm_token(user)
    link = url_for("auth.confirm_email", token=token, _external=True)
    body = (
        f"Hallo {user.username},\n\n"
        f"bitte bestätige deine E-Mail-Adresse für FlightDeck DG Hub:\n{link}\n\n"
        "Der Link ist 24 Stunden gültig."
    )
    return _send("FlightDeck DG Hub – E-Mail bestätigen", user.email, body)


def send_password_reset_email(user) -> bool:
    token = generate_reset_token(user)
    link = url_for("auth.reset_password", token=token, _external=True)
    body = (
        f"Hallo {user.username},\n\n"
        f"du hast ein neues Passwort angefordert. Link (1 Stunde gültig):\n{link}\n\n"
        "Falls du das nicht warst, ignoriere diese E-Mail."
    )
    return _send("FlightDeck DG Hub – Passwort zurücksetzen", user.email, body)


def send_test_email(recipient: str) -> bool:
    body = "Dies ist eine Testmail von FlightDeck DG Hub, ausgelöst über das Admin-Dashboard."
    return _send("FlightDeck DG Hub – Testmail", recipient, body)
