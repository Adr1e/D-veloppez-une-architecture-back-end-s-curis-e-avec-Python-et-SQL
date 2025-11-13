"""User repository.

This module contains all database operations related to users.
Keeping queries here makes the service and CLI layers easier to maintain.
"""

from __future__ import annotations
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from ..models import User, Role, Department


# Basic lookups
def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Return a user object matching the email, or None if not found."""
    return db.query(User).filter(User.email == email).one_or_none()


def resolve_role_id(db: Session, role_name: str) -> Optional[int]:
    """Return the ID of a role by name, or None if the role does not exist."""
    role = db.query(Role).filter(Role.name == role_name).one_or_none()
    return role.id if role else None


def resolve_department_id(db: Session, name: str) -> Optional[int]:
    """Return the ID of a department by name, or None if not found."""
    dep = db.query(Department).filter(Department.name == name).one_or_none()
    return dep.id if dep else None


# Write operations
def create_user_row(
    db: Session,
    *,
    email: str,
    full_name: str,
    password_hash: str,
    employee_number: str | None,
    role_id: int | None,
    department_id: int | None,
) -> User:
    """
    Create a new user row in the database.

    Args:
        db: The active database session.
        email: Email of the new user.
        full_name: Full name of the user.
        password_hash: Hashed password.
        employee_number: Optional employee number.
        role_id: Optional role ID.
        department_id: Optional department ID.

    Returns:
        The newly created User object.
    """
    user = User(
        email=email,
        full_name=full_name,
        password_hash=password_hash,
        employee_number=employee_number,
        role_id=role_id,
        department_id=department_id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_all_users(db: Session) -> Iterable[User]:
    """Return all users sorted by email for predictable ordering."""
    return db.query(User).order_by(User.email.asc()).all()


def delete_user_by_email(db: Session, email: str) -> bool:
    """
    Delete a user by email.

    Returns:
        True if the user existed and was removed, otherwise False.
    """
    user = get_user_by_email(db, email)
    if not user:
        return False

    db.delete(user)
    db.commit()
    return True
