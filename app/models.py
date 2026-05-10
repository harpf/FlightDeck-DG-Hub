from datetime import datetime
import secrets

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    privacy_consent = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    reviews = db.relationship("ProductReview", back_populates="user", lazy=True)
    source_requests = db.relationship("SourceRequest", back_populates="requested_by", lazy=True)
    api_tokens = db.relationship("ApiToken", back_populates="created_by", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    manufacturer = db.Column(db.String(255))
    category = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    product_url = db.Column(db.String(500))
    disc_type = db.Column(db.String(80))
    speed = db.Column(db.Integer)
    glide = db.Column(db.Integer)
    turn = db.Column(db.Integer)
    fade = db.Column(db.Integer)
    diameter_cm = db.Column(db.Float)
    weight_range_g = db.Column(db.String(32))
    plastic_type = db.Column(db.String(120))
    stability = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    reviews = db.relationship("ProductReview", back_populates="product", lazy=True, cascade="all, delete-orphan")


class ProductReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    user = db.relationship("User", back_populates="reviews")
    product = db.relationship("Product", back_populates="reviews")
    __table_args__ = (db.UniqueConstraint("user_id", "product_id", name="uq_user_product_review"),)


class SourceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_url = db.Column(db.String(500), nullable=False)
    note = db.Column(db.Text)
    status = db.Column(db.String(20), default="open", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    requested_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    requested_by = db.relationship("User", back_populates="source_requests")


class ApiToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    token_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_by = db.relationship("User", back_populates="api_tokens")

    @staticmethod
    def generate_secret() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def build_plaintext_token(token_id: int, secret: str) -> str:
        return f"{token_id}.{secret}"

    def set_secret(self, secret: str) -> None:
        self.token_hash = generate_password_hash(secret)

    def check_secret(self, secret: str) -> bool:
        return self.is_active and check_password_hash(self.token_hash, secret)


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))
