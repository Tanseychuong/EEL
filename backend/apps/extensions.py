"""
Flask extension instances, initialized without an app (the app factory in
app/__init__.py calls .init_app() on each). Keeping these here — separate
from models.py — is what lets models.py, blueprints, and the factory all
import `db` without circular-import issues.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

# Rate limiting protects the opportunity-submission and auth endpoints from
# abuse. Storage defaults to in-memory (fine for one dev/small instance);
# point RATELIMIT_STORAGE_URI at Redis once you're running more than one
# backend process, since in-memory limits don't share state across processes.
limiter = Limiter(key_func=get_remote_address)
