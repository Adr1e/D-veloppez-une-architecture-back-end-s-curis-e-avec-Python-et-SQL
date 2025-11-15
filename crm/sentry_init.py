from __future__ import annotations

# Silence chatty bcrypt version probe from passlib in case Sentry imports it
import logging
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)

"""
Minimal Sentry bootstrap.

Why:
- Central place to configure Sentry (error monitoring).
- Safe no-op if SENTRY_DSN is not set, so local dev is unaffected.
"""

import os


def init_sentry() -> None:
    """
    Initialize Sentry only if a DSN is provided.

    Env vars:
    - SENTRY_DSN: project DSN (empty -> no-op)
    - SENTRY_ENV: environment name (e.g., 'development', 'production')
    - SENTRY_TRACES: traces sample rate (string float, default '0.0')
    """
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        # No DSN -> do nothing (keep CLI fast and silent in dev)
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.excepthook import ExcepthookIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("SENTRY_ENV", "development"),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES", "0.0")),
            integrations=[
                ExcepthookIntegration(),   # capture unexpected exceptions
                SqlalchemyIntegration(),    # capture DB-level errors
                LoggingIntegration(level=None, event_level=None),
            ],
        )
    except Exception as exc:  # pragma: no cover
        # Never block the app if Sentry fails to initialize
        print(f"[sentry] init skipped: {exc}")
