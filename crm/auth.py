"""Authentication and authorization helpers."""

from typing import Optional
from .principal import Principal


def ensure_admin(principal: Optional[Principal]) -> None:
    """
    Ensure that the current user has the admin role ("gestion").

    Args:
        principal: The authenticated user information.

    Raises:
        PermissionError: If the user is missing or does not have the admin role.
    """
    if not principal or principal.role != "gestion":
        raise PermissionError("admin privileges required (role 'gestion').")


def ensure_permission(principal: Optional[Principal], needed_code: str, user_has_codes: set[str]) -> None:
    """
    Ensure that the current user has a specific permission code.

    Args:
        principal: The authenticated user information.
        needed_code: The required permission code.
        user_has_codes: The set of permission codes assigned to the user.

    Raises:
        PermissionError: If the user is missing or lacks the needed permission.
    """
    if not principal:
        raise PermissionError("authentication required")
    if needed_code not in user_has_codes:
        raise PermissionError(f"missing permission: {needed_code}")
