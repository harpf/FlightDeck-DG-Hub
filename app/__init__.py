import logging

from flask import Flask, render_template

from config import Config
from app.extensions import db, login_manager, migrate
from app.models import User
from app.routes import api_bp, auth_bp, events_bp, main_bp, members_bp, roles_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(roles_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(api_bp)

    configure_logging(app)
    register_error_handlers(app)
    register_cli_commands(app)

    return app


def configure_logging(app: Flask) -> None:
    if not app.debug:
        logging.basicConfig(level=logging.INFO)


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
        username = "admin"
        password = "admin1234"
        user = User.query.filter_by(username=username).first()
        if user:
            print("Admin existiert bereits.")
            return

        user = User(username=username, is_admin=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        print("Admin erstellt: admin / admin1234")
