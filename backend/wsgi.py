"""
Production WSGI entry point. Point your server at this, e.g.:

    gunicorn "wsgi:app" --workers 4 --bind 0.0.0.0:8000

Workers > 1 is why RATELIMIT_STORAGE_URI and any future caching need to be
Redis-backed rather than in-memory once you deploy — in-memory state isn't
shared across worker processes.
"""

from app import create_app

app = create_app(config_name="production")
