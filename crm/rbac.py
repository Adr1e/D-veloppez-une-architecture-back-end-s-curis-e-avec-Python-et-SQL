"""RBAC helpers: load permissions for the current user role."""

from __future__ import annotations

from typing import Set
from sqlalchemy.orm import Session

from .models import Role, Permission, RolePermission
from .principal import Principal


def get_user_permissions(db: Session, principal: Principal) -> Set[str]:
    """
    Return the set of permission codes for the given principal's role.

    Example codes (see seeds):
        - client.read / client.write
        - contract.read / contract.write
        - event.read / event.write
        - user.admin
    """
    if principal is None or principal.role is None:
        return set()

    role = db.query(Role).filter(Role.name == principal.role).one_or_none()
    if not role:
        return set()

    rows = (
        db.query(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .filter(RolePermission.role_id == role.id)
        .all()
    )

    return {code for (code,) in rows}
