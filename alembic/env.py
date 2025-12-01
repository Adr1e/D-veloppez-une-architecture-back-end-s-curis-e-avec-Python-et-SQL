"""Alembic environment.

Key points:
- Import Base.metadata to let --autogenerate see models.
- render_as_batch=True is required for SQLite to alter tables safely.
"""
from __future__ import annotations

# Add project root to Python path so Alembic can import the crm package.
# Alembic runs env.py from the alembic folder. Because of this relative path,
# Python cannot automatically find the crm package located one level higher.
# These lines compute the project root and add it to sys.path at runtime.
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parents[1]
sys.path.append(str(project_root))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Alembic Config object, gives access to values from alembic.ini.
config = context.config

# Load logging configuration if present.
if config.config_file_name:
    fileConfig(config.config_file_name)

# Import Base metadata from the crm package.
# Alembic uses this metadata to detect schema changes.
from crm.models import Base
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode.
    In this mode, Alembic generates SQL scripts without connecting to the database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True  # Required for SQLite to support table alterations.
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode.
    In this mode, Alembic connects to the database and applies migrations directly.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True  # Required for SQLite when altering tables.
        )

        with context.begin_transaction():
            context.run_migrations()


# Check whether Alembic is running offline or online.
# Call the appropriate migration function.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
