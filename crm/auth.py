"""Authentication and authorization helpers."""

from __future__ import annotations

import getpass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import jwt
import sentry_sdk

from .config import JWT_SECRET, JWT_ALGORITHM, JWT_EXP_DELTA, TOKEN_FILE_NAME
from .db import get_db
from .models import User
from .principal import Principal, principal_from_email
from .security import verify_password


# TOKEN MANAGEMENT (JWT)

TOKEN_PATH = Path.home() / TOKEN_FILE_NAME


class AuthError(Exception):
    """Raised when authentication fails."""


def _encode_token(user: User) -> str:
    """Create a signed JWT for the given user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "iat": int(now.timestamp()),
        "exp": int((now + JWT_EXP_DELTA).timestamp()),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token if isinstance(token, str) else token.decode("utf-8")


def _save_token(token: str) -> None:
    """Store the JWT token in a file in the user's home directory."""
    TOKEN_PATH.write_text(token, encoding="utf-8")


def _load_token() -> Optional[str]:
    """Read the JWT token from disk, if present."""
    if not TOKEN_PATH.exists():
        return None
    content = TOKEN_PATH.read_text(encoding="utf-8").strip()
    return content or None


def logout() -> None:
    """Remove local token file (logout)."""
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()


def authenticate(email: str, password: str) -> Principal:
    """
    Authenticate a user and store its JWT locally.

    Returns:
        Principal: the authenticated principal.

    Raises:
        AuthError: if the user does not exist or the password is invalid.
    """
    with get_db() as db:
        user = db.query(User).filter(User.email == email).one_or_none()

        if user is None:
            raise AuthError("Unknown user.")

        if not verify_password(password, user.password_hash):
            raise AuthError("Invalid password.")

        # JWT pour l'auth persistante
        token = _encode_token(user)
        _save_token(token)

        # On construit le Principal via la fonction existante
        principal = principal_from_email(db, user.email)
        return principal


def login_cli() -> None:
    """Interactive CLI login command."""
    print("== Epic Events Login ==")
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")

    try:
        principal = authenticate(email, password)
        # Principal n'a pas full_name, on affiche l'email
        print(f"Logged in as {principal.email} ✓")
    except AuthError as exc:
        print(f"Authentication error: {exc}")


def get_current_principal() -> Principal:
    """
    Return the authenticated user (Principal) from the stored JWT.

    Raises:
        AuthError: if no token is stored, expired, invalid or user not found.
    """
    token = _load_token()
    if not token:
        raise AuthError("No stored token. Please login first.")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        sentry_sdk.capture_exception(exc)
        logout()
        raise AuthError("Session expired. Please log in again.")
    except jwt.InvalidTokenError as exc:
        sentry_sdk.capture_exception(exc)
        logout()
        raise AuthError("Invalid token. Please log in again.")

    user_id = int(payload["sub"])

    with get_db() as db:
        user = db.get(User, user_id)
        if not user:
            raise AuthError("User from token not found.")

        # On reconstruit le Principal à partir de l'email
        principal = principal_from_email(db, user.email)
        return principal


# AUTHORIZATION HELPERS

def ensure_admin(principal: Optional[Principal]) -> None:
    """
    Ensure that the current principal has the admin role ('gestion').
    """
    if not principal or principal.role != "gestion":
        raise PermissionError("admin privileges required (role 'gestion').")


def ensure_permission(
    principal: Optional[Principal],
    needed_code: str,
    user_has_codes: set[str],
) -> None:
    """
    Ensure that the current principal has a specific permission code.
    """
    if not principal:
        raise PermissionError("authentication required")
    if needed_code not in user_has_codes:
        raise PermissionError(f"missing permission: {needed_code}")
