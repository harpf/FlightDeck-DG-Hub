from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class MemberRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    members = db.relationship("Member", back_populates="role", lazy=True)


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True)
    phone = db.Column(db.String(64))
    street = db.Column(db.String(255))
    zip_code = db.Column(db.String(20))
    city = db.Column(db.String(120))
    join_date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    notes = db.Column(db.Text)

    role_id = db.Column(db.Integer, db.ForeignKey("member_role.id"), nullable=True)
    role = db.relationship("MemberRole", back_populates="members")

    registrations = db.relationship("MemberEventRegistration", back_populates="member", lazy=True)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(255))
    event_date = db.Column(db.DateTime, nullable=False)

    registrations = db.relationship("MemberEventRegistration", back_populates="event", lazy=True)


class MemberEventRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    member = db.relationship("Member", back_populates="registrations")
    event = db.relationship("Event", back_populates="registrations")

    __table_args__ = (db.UniqueConstraint("member_id", "event_id", name="uq_member_event"),)


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))
