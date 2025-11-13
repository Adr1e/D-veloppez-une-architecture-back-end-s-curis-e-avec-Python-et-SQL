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
from pydantic import BaseModel


class Settings(BaseModel):
    """Typed config object for all application settings."""

    # SQLite file in project root by default (works out of the box)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./epic_events.db")

    # Optional Sentry DSN for error tracking
    SENTRY_DSN: str | None = os.getenv("SENTRY_DSN")

    # Environment name used by Sentry (for example: development, staging, production)
    SENTRY_ENV: str = os.getenv("SENTRY_ENV", "development")

    # Sample rate for Sentry performance tracing
    SENTRY_TRACES: float = float(os.getenv("SENTRY_TRACES", "0.0"))


# Create a single shared settings instance for the whole application
settings = Settings()
