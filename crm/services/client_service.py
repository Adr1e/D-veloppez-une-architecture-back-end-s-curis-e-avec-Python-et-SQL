"""Services for creating and updating clients."""

from __future__ import annotations

from typing import Dict, Any
from sqlalchemy.orm import Session

from ..models import Client
from ..principal import Principal
from ..auth import ensure_permission
from ..rbac import get_user_permissions


def _ensure_authenticated(principal: Principal) -> None:
    if principal is None:
        raise PermissionError("Authentication required.")


def create_client(
    db: Session,
    principal: Principal,
    data: Dict[str, Any],
) -> Client:
    """
    Create a new client.

    Notes:
        - Requires 'client.write' permission.
        - 'data' is a dict of fields passed to the Client constructor.
          Example:
            {
                "full_name": "Client Test",
                "email": "client@test.com",
                "company_name": "ACME",
                "phone": "+33..."
            }
    """
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "client.write", perms)

    client = Client(**data)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def update_client(
    db: Session,
    principal: Principal,
    client_id: int,
    data: Dict[str, Any],
) -> Client:
    """
    Update an existing client.

    Notes:
        - Requires 'client.write' permission.
        - Only fields that exist on the model are updated.
    """
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "client.write", perms)

    client = db.get(Client, client_id)
    if not client:
        raise ValueError(f"Client {client_id} not found")

    for key, value in data.items():
        if hasattr(client, key):
            setattr(client, key, value)

    db.commit()
    db.refresh(client)
    return client
