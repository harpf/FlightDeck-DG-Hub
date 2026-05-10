import logging

from flask import Flask, render_template

from config import Config
from app.extensions import db, login_manager, migrate
from app.models import User
from app.routes import admin_bp, api_bp, auth_bp, main_bp, products_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    configure_logging(app)
    register_error_handlers(app)
    register_cli_commands(app)
    register_security_headers(app)

    return app


def configure_logging(app: Flask) -> None:
    if not app.debug:
        logging.basicConfig(level=logging.INFO)


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def secure_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;"
        return response


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(403)
    def forbidden(_err):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_err):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal(_err):
        return render_template("errors/500.html"), 500


def register_cli_commands(app: Flask) -> None:
    @app.cli.command("create-admin")
    def create_admin_command():
        password = app.config.get("BOOTSTRAP_ADMIN_PASSWORD")
        if not password:
            print("BOOTSTRAP_ADMIN_PASSWORD nicht gesetzt. Admin wurde NICHT erstellt.")
            return
        user = User.query.filter_by(username="admin").first()
        if user:
            print("Admin existiert bereits.")
            return

        user = User(username="admin", email="admin@flightdeck.local", is_admin=True, privacy_consent=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print("Admin erstellt.")
