"""Application configuration.

Purpose:
- Centralize runtime configuration (DB url, env flags, etc.).
- Avoid hard-coding values in the rest of the codebase.

Notes:
- Default values are safe for local development.
- Values can be overridden with environment variables.
"""
from __future__ import annotations

import os
from datetime import timedelta
from pydantic import BaseModel

# JWT CONFIGURATION
JWT_SECRET = os.environ.get("EPICEVENTS_JWT_SECRET", "change-me-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA = timedelta(hours=1)
TOKEN_FILE_NAME = ".epicevents_token"  # Stored in user HOME directory


# APPLICATION SETTINGS
class Settings(BaseModel):
    """Typed config object for all application settings."""

    # SQLite file in project root
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./epic_events.db")

    # Optional Sentry DSN for error tracking
    SENTRY_DSN: str | None = os.getenv("SENTRY_DSN")

    # Environment name used by Sentry
    SENTRY_ENV: str = os.getenv("SENTRY_ENV", "development")

    # Sample rate for tracing
    SENTRY_TRACES: float = float(os.getenv("SENTRY_TRACES", "0.0"))


# Shared settings instance
settings = Settings()
