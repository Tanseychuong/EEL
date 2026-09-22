"""
Flask application factory. create_app() is what wsgi.py, manage.py, and
tests all call — nothing outside this file should import a global `app`.
"""

import os
import logging

from flask import Flask, jsonify

from config import config_by_name
from apps.extensions import db, migrate, jwt, cors, limiter


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_cli(app)
    _configure_logging(app)

    @app.get("/health")
    def health():
        # Cheap liveness check — point your host's health check / uptime
        # monitor here rather than at a real endpoint.
        return jsonify(status="ok"), 200

    return app


def _init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    limiter.init_app(app)


def _register_blueprints(app):
    from apps.blueprints.auth.routes import auth_bp
    from apps.blueprints.opportunities.routes import opportunities_bp
    from apps.blueprints.admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(opportunities_bp, url_prefix="/api/opportunities")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Not found"), 404

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error=str(e.description) if hasattr(e, "description") else "Bad request"), 400

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify(error="Too many requests, slow down"), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled server error")
        return jsonify(error="Internal server error"), 500


def _register_cli(app):
    from apps.cli import register_commands
    register_commands(app)


def _configure_logging(app):
    if not app.debug and not app.testing:
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
