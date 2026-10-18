import os

from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from config import config_by_name
from .extensions import csrf, db, login_manager, migrate, socketio


def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_by_name[config_name])

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio.init_app(
        app,
        async_mode=app.config.get("SOCKETIO_ASYNC_MODE"),
        message_queue=app.config.get("SOCKETIO_MESSAGE_QUEUE"),
        cors_allowed_origins=[],
    )

    from . import models  # noqa: F401
    from .auth.routes import auth_bp
    from .main.routes import main_bp
    from .listings.routes import listings_bp
    from .favourites.routes import favourites_bp
    from .chat.routes import chat_bp
    from .chat import events  # noqa: F401
    from .reports.routes import reports_bp
    from .admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(listings_bp)
    app.register_blueprint(favourites_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)

    register_error_handlers(app)
    register_context(app)
    register_cli(app)
    return app


def _wants_json():
    return request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json"


def register_error_handlers(app):
    def render_error(code, title, message):
        if _wants_json():
            return jsonify(error=message), code
        return render_template("errors/error.html", code=code, title=title, message=message), code

    @app.errorhandler(403)
    def forbidden(_e):
        return render_error(403, "Access denied", "You don't have permission to view this page.")

    @app.errorhandler(404)
    def not_found(_e):
        return render_error(404, "Page not found", "The page you're looking for doesn't exist or was removed.")

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_e):
        mb = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        return render_error(413, "Upload too large", f"Uploaded files must be under {mb} MB in total.")

    @app.errorhandler(500)
    def server_error(_e):
        db.session.rollback()
        return render_error(500, "Something went wrong", "An unexpected error occurred. Please try again.")

    from flask_wtf.csrf import CSRFError

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return render_error(400, "Invalid request", "Your session expired or the form was tampered with. Please try again.")


def register_context(app):
    from flask_login import current_user
    from . import constants
    from .chat.services import unread_count_for

    @app.context_processor
    def inject_globals():
        unread = unread_count_for(current_user) if current_user.is_authenticated else 0
        return {
            "CATEGORIES": constants.CATEGORIES,
            "CONDITIONS": constants.CONDITIONS,
            "COURSES": constants.COURSES,
            "YEARS": constants.YEARS,
            "SORT_OPTIONS": constants.SORT_OPTIONS,
            "unread_messages": unread,
            "chat_poll_interval": app.config["CHAT_POLL_INTERVAL_MS"],
        }

    @app.template_filter("inr")
    def inr(value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "₹0"
        if value == int(value):
            return f"₹{int(value):,}"
        return f"₹{value:,.2f}"

    @app.template_filter("timeago")
    def timeago(dt):
        from datetime import datetime, timezone

        if dt is None:
            return ""
        now = datetime.utcnow()
        diff = now - dt
        secs = int(diff.total_seconds())
        if secs < 60:
            return "just now"
        if secs < 3600:
            return f"{secs // 60} min ago"
        if secs < 86400:
            return f"{secs // 3600} hr ago"
        if secs < 7 * 86400:
            return f"{secs // 86400} d ago"
        return dt.strftime("%d %b %Y")


def register_cli(app):
    import click

    @app.cli.command("seed")
    @click.option("--reset", is_flag=True, help="Delete existing data before seeding.")
    def seed_command(reset):
        """Populate the database with NWCC demo users and listings."""
        from seed import run_seed

        run_seed(reset=reset)
        click.echo("Seed complete.")

    @app.cli.command("make-admin")
    @click.argument("email")
    def make_admin(email):
        """Grant report-review access to a user."""
        from .models import User

        user = User.query.filter_by(email=email.lower()).first()
        if not user:
            click.echo("No user with that email.")
            return
        user.is_admin = True
        db.session.commit()
        click.echo(f"{email} is now an admin.")
