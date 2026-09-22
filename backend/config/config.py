"""
Environment-driven configuration. Nothing here is hard-coded so the same
codebase runs in dev, test, and production off different env vars —
required for deploying frontend/backend separately (Vercel + Render/Railway)
and for ever running more than one backend instance.
"""

import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://localhost:5432/eel"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Connection pooling — matters once you have concurrent requests, so it's
    # configured from day one rather than left on SQLAlchemy's defaults.
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.environ.get("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 20)),
        "pool_pre_ping": True,       # avoids "server closed the connection" errors
        "pool_recycle": 280,         # recycle before most providers' idle timeout
    }

    # Auth
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Pagination — every list endpoint (opportunities, admin queues) should
    # read these rather than hard-coding page sizes, so one place controls
    # payload size as the dataset grows.
    DEFAULT_PAGE_SIZE = int(os.environ.get("DEFAULT_PAGE_SIZE", 20))
    MAX_PAGE_SIZE = int(os.environ.get("MAX_PAGE_SIZE", 100))

    # Premium early-access window — mirrors models.EARLY_ACCESS_WINDOW but
    # exposed as config too, in case you want it adjustable without a deploy.
    EARLY_ACCESS_HOURS = int(os.environ.get("EARLY_ACCESS_HOURS", 48))

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Rate limiting storage — "memory://" is fine for a single process;
    # swap to a Redis URL once you run more than one backend instance,
    # or limits stop being shared across processes.
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL", "sqlite:///:memory:"
    )
    # SQLite has no connection pool in the same sense — drop the Postgres-only options
    SQLALCHEMY_ENGINE_OPTIONS = {}


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self):
        # Fail fast in production if secrets were left on their dev defaults.
        assert os.environ.get("SECRET_KEY"), "SECRET_KEY must be set in production"
        assert os.environ.get("JWT_SECRET_KEY"), "JWT_SECRET_KEY must be set in production"
        assert os.environ.get("DATABASE_URL"), "DATABASE_URL must be set in production"


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
