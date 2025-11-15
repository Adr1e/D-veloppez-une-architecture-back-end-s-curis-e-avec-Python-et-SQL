from __future__ import annotations
from typing import Optional

from sqlalchemy.orm import Session
import sentry_sdk

from ..models import User, Role
from ..auth import ensure_admin, Principal
from ..security import hash_password


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Return a user object by email, or None if not found."""
    return db.query(User).filter(User.email == email).one_or_none()


def create_user(
    db: Session,
    *,
    email: str,
    full_name: Optional[str] = None,
    password_plain: Optional[str] = None,
    employee_number: Optional[str] = None,
) -> User:
    """
    Create a new user with a hashed password.

    Notes:
        - If the user already exists, the existing user is returned.
        - If no password is provided, a default placeholder is used.

    Returns:
        The newly created or existing User object.
    """
    existing = get_user_by_email(db, email)
    if existing:
        return existing

    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password_plain or "changeme"),
        employee_number=employee_number,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Journalisation Sentry : création d’un collaborateur
    sentry_sdk.capture_message(
        f"User created: {user.email}",
        level="info",
    )

    return user


def promote_user_to_role(db: Session, *, email: str, role_name: str = "gestion") -> bool:
    """
    Assign a role to a user.

    Args:
        email: User's email.
        role_name: Name of the role to assign.

    Returns:
        True if the operation succeeded, False if the user was not found.
    """
    user = get_user_by_email(db, email)
    if not user:
        return False

    role = db.query(Role).filter(Role.name == role_name).one_or_none()

    # Create the role if it does not exist
    if not role:
        role = Role(name=role_name, description=f"Role {role_name}")
        db.add(role)
        db.flush()

    user.role_id = role.id
    db.commit()

    # Journalisation Sentry : modification / promotion d’un collaborateur
    sentry_sdk.capture_message(
        f"User {email} promoted to role {role_name}",
        level="info",
    )

    return True


def set_password(db: Session, *, email: str, new_password_plain: str) -> bool:
    """
    Update a user's password.

    Args:
        email: User's email.
        new_password_plain: The new password in plain text.

    Returns:
        True if the password was updated, False if the user was not found.
    """
    user = get_user_by_email(db, email)
    if not user:
        return False

    user.password_hash = hash_password(new_password_plain)
    db.commit()

    # Journalisation Sentry (bonus)
    sentry_sdk.capture_message(
        f"Password updated for user {email}",
        level="info",
    )

    return True


def delete_user(db: Session, *, principal: Optional[Principal], email: str) -> bool:
    """
    Delete a user from the system.

    Notes:
        - Requires an admin principal (role 'gestion').
        - Returns False if the user does not exist.

    Args:
        principal: The acting authenticated user.
        email: Email of the user to delete.

    Returns:
        True if the user was deleted, False otherwise.
    """
    ensure_admin(principal)

    user = get_user_by_email(db, email)
    if not user:
        return False

    db.delete(user)
    db.commit()

    # Journalisation Sentry (bonus)
    sentry_sdk.capture_message(
        f"User deleted: {email}",
        level="warning",
    )

    return True
