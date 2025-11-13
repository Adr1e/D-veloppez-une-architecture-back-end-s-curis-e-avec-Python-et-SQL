"""Represents the authenticated user (principal) and helpers to load it."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session

from .models import User, Role


@dataclass
class Principal:
    """
    Simple object representing the current authenticated user.

    Attributes:
        id: The user's database ID.
        email: The user's email address.
        role: The user's role name (e.g., 'gestion', 'commercial', 'support').
    """
    id: int
    email: str
    role: Optional[str]


def principal_from_email(db: Session, email: str) -> Optional[Principal]:
    """
    Load a Principal object from a user's email.

    Args:
        db: The active database session.
        email: The email of the user to fetch.

    Returns:
        Principal object if the user exists, otherwise None.
    """
    user = db.query(User).filter(User.email == email).one_or_none()
    if not user:
        return None

    # Extract the role name if the user has a role assigned
    role_name = user.role.name if user.role else None

    return Principal(
        id=user.id,
        email=user.email,
        role=role_name,
    )
