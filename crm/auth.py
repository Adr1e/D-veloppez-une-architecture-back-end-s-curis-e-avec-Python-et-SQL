"""
Authentication and authorization helpers.

This module provides:
- JWT token creation, storage, and validation
- Login/logout functionality
- Permission checking utilities
"""

from __future__ import annotations

import getpass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set

import jwt
import sentry_sdk

from .config import JWT_SECRET, JWT_ALGORITHM, JWT_EXP_DELTA, TOKEN_FILE_NAME
from .db import get_db
from .models import User
from .principal import Principal, principal_from_email
from .security import verify_password
from .exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    NotAuthenticatedError,
    AdminRequiredError,
    PermissionDeniedError,
)


# =============================================================================
# TOKEN MANAGEMENT
# =============================================================================

TOKEN_PATH = Path.home() / TOKEN_FILE_NAME


# Keep AuthError as an alias for backward compatibility
AuthError = AuthenticationError


def _encode_token(user: User) -> str:
    """Create a signed JWT for the given user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,  # Include email for debugging
        "iat": int(now.timestamp()),
        "exp": int((now + JWT_EXP_DELTA).timestamp()),
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token if isinstance(token, str) else token.decode("utf-8")


def _save_token(token: str) -> None:
    """Store the JWT token in a file in the user's home directory."""
    try:
        TOKEN_PATH.write_text(token, encoding="utf-8")
        # Set restrictive permissions (owner only)
        TOKEN_PATH.chmod(0o600)
    except OSError as e:
        sentry_sdk.capture_exception(e)
        raise AuthenticationError(f"Impossible de sauvegarder le token: {e}")


def _load_token() -> Optional[str]:
    """Read the JWT token from disk, if present."""
    if not TOKEN_PATH.exists():
        return None
    try:
        content = TOKEN_PATH.read_text(encoding="utf-8").strip()
        return content or None
    except OSError as e:
        sentry_sdk.capture_exception(e)
        return None


def logout() -> None:
    """Remove local token file (logout)."""
    try:
        if TOKEN_PATH.exists():
            TOKEN_PATH.unlink()
    except OSError as e:
        sentry_sdk.capture_exception(e)
        # Don't raise - logout should always "succeed" from user perspective


# =============================================================================
# AUTHENTICATION
# =============================================================================

def authenticate(email: str, password: str) -> Principal:
    """
    Authenticate a user and store its JWT locally.

    Args:
        email: User's email address.
        password: User's plain text password.

    Returns:
        Principal: The authenticated principal.

    Raises:
        InvalidCredentialsError: If email or password is incorrect.
        AuthenticationError: If there's a system error during authentication.
    """
    if not email or not password:
        raise InvalidCredentialsError()

    with get_db() as db:
        user = db.query(User).filter(User.email == email).one_or_none()

        if user is None:
            # Log failed attempt (without revealing if user exists)
            sentry_sdk.capture_message(
                f"Failed login attempt for email: {email}",
                level="warning",
            )
            raise InvalidCredentialsError()

        if not verify_password(password, user.password_hash):
            sentry_sdk.capture_message(
                f"Failed login attempt (wrong password) for: {email}",
                level="warning",
            )
            raise InvalidCredentialsError()

        # Create and save JWT
        token = _encode_token(user)
        _save_token(token)

        # Build Principal
        principal = principal_from_email(db, user.email)
        
        # Log successful login
        sentry_sdk.capture_message(
            f"User logged in: {email}",
            level="info",
        )
        
        return principal


def login_cli() -> None:
    """Interactive CLI login command."""
    print("== Epic Events - Connexion ==")
    email = input("Email: ").strip()
    
    if not email:
        print("Email requis.")
        return
    
    password = getpass.getpass("Mot de passe: ")

    try:
        principal = authenticate(email, password)
        role_info = f" (rôle: {principal.role})" if principal.role else ""
        print(f"✓ Connecté en tant que {principal.email}{role_info}")
    except InvalidCredentialsError:
        print("✗ Email ou mot de passe incorrect.")
    except AuthenticationError as exc:
        print(f"✗ Erreur d'authentification: {exc}")


def get_current_principal() -> Principal:
    """
    Return the authenticated user (Principal) from the stored JWT.

    Returns:
        Principal: The current authenticated user.

    Raises:
        NotAuthenticatedError: If no token is stored.
        TokenExpiredError: If the token has expired.
        TokenInvalidError: If the token is malformed.
        AuthenticationError: If user not found in database.
    """
    token = _load_token()
    if not token:
        raise NotAuthenticatedError()

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        sentry_sdk.capture_exception(exc)
        logout()
        raise TokenExpiredError()
    except jwt.InvalidTokenError as exc:
        sentry_sdk.capture_exception(exc)
        logout()
        raise TokenInvalidError()

    user_id = int(payload["sub"])

    with get_db() as db:
        user = db.get(User, user_id)
        if not user:
            logout()
            raise AuthenticationError(
                "L'utilisateur associé à ce token n'existe plus."
            )

        principal = principal_from_email(db, user.email)
        return principal


def is_authenticated() -> bool:
    """
    Check if there is a valid authenticated session.
    
    Returns:
        True if user is authenticated, False otherwise.
    """
    try:
        get_current_principal()
        return True
    except AuthenticationError:
        return False


# =============================================================================
# AUTHORIZATION HELPERS
# =============================================================================

def ensure_admin(principal: Optional[Principal]) -> None:
    """
    Ensure that the current principal has the admin role ('gestion').
    
    Args:
        principal: The principal to check.
        
    Raises:
        NotAuthenticatedError: If principal is None.
        AdminRequiredError: If principal is not an admin.
    """
    if not principal:
        raise NotAuthenticatedError()
    
    if principal.role != "gestion":
        raise AdminRequiredError()


def ensure_permission(
    principal: Optional[Principal],
    needed_code: str,
    user_has_codes: Set[str],
) -> None:
    """
    Ensure that the current principal has a specific permission code.
    
    Args:
        principal: The principal to check.
        needed_code: The permission code required.
        user_has_codes: Set of permission codes the user has.
        
    Raises:
        NotAuthenticatedError: If principal is None.
        PermissionDeniedError: If permission is missing.
    """
    if not principal:
        raise NotAuthenticatedError()
    
    if needed_code not in user_has_codes:
        raise PermissionDeniedError(needed_code)


def ensure_any_permission(
    principal: Optional[Principal],
    needed_codes: list[str],
    user_has_codes: Set[str],
) -> None:
    """
    Ensure that the principal has at least one of the required permissions.
    
    Args:
        principal: The principal to check.
        needed_codes: List of permission codes (any one is sufficient).
        user_has_codes: Set of permission codes the user has.
        
    Raises:
        NotAuthenticatedError: If principal is None.
        PermissionDeniedError: If no required permission is present.
    """
    if not principal:
        raise NotAuthenticatedError()
    
    if not any(code in user_has_codes for code in needed_codes):
        raise PermissionDeniedError(
            permission=", ".join(needed_codes),
            action="cette action (au moins une permission requise)"
        )


def get_role(principal: Optional[Principal]) -> Optional[str]:
    """
    Get the role name of the principal.
    
    Args:
        principal: The principal.
        
    Returns:
        Role name or None if not authenticated.
    """
    if not principal:
        return None
    return principal.role