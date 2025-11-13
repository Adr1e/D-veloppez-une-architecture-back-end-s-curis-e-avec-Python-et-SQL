"""Database session utilities."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .config import settings

#  Engine & Session factory 
# Create the SQLAlchemy engine from the configured DATABASE_URL.
engine = create_engine(settings.DATABASE_URL, future=True, echo=False)

# Session factory used everywhere in the app.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=True,
    future=True,
)

@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Yield a SQLAlchemy Session and always close it.

    Why:
    - Using @contextmanager lets `with get_db() as db:` work correctly.
    - We commit on success, rollback on error, and close in all cases.

    Returns:
        A generator that yields a Session object.
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()          # safe: no-op if nothing was changed
    except Exception:
        db.rollback()        # keep DB consistent on error
        raise
    finally:
        db.close()           # free connection/resources
