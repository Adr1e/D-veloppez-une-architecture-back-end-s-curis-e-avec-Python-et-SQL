"""
Services for creating and updating clients.

Business rules (from specification):
- Commercial users can CREATE clients (auto-assigned to them)
- Commercial users can only UPDATE clients they are responsible for
- Gestion users can create/update any client
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
import sentry_sdk

from ..models import Client, User
from ..principal import Principal
from ..auth import ensure_permission
from ..rbac import get_user_permissions


class ClientOwnershipError(PermissionError):
    """Raised when a user tries to modify a client they don't own."""
    
    def __init__(self, client_id: int, user_email: str):
        self.client_id = client_id
        self.user_email = user_email
        super().__init__(
            f"Vous n'êtes pas le commercial responsable du client {client_id}. "
            f"Seul le commercial assigné peut modifier ce client."
        )


def _ensure_authenticated(principal: Optional[Principal]) -> None:
    """Raise if no authenticated user is provided."""
    if principal is None:
        raise PermissionError("Authentification requise.")


def _is_gestion(principal: Principal) -> bool:
    """Check if the principal has the 'gestion' (admin) role."""
    return principal.role == "gestion"


def _check_client_ownership(
    db: Session,
    principal: Principal,
    client: Client,
) -> None:
    """
    Verify that the principal is allowed to modify this client.
    
    Rules:
    - Gestion users can modify any client
    - Commercial users can only modify clients where they are the sales_contact
    
    Raises:
        ClientOwnershipError: If the user doesn't have permission.
    """
    if _is_gestion(principal):
        return  # Admin can modify anything
    
    # For commercial/support: check ownership
    if client.sales_contact_id != principal.id:
        raise ClientOwnershipError(client.id, principal.email)


def create_client(
    db: Session,
    principal: Principal,
    data: Dict[str, Any],
) -> Client:
    """
    Create a new client.

    Business rules:
    - Requires 'client.write' permission.
    - For commercial users, the client is automatically assigned to them.
    - For gestion users, they can optionally specify a sales_contact_id.

    Args:
        db: Database session.
        principal: The authenticated user.
        data: Client data dictionary.

    Returns:
        The newly created Client object.

    Raises:
        PermissionError: If user lacks permission.
    """
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "client.write", perms)

    # Auto-assign commercial contact for non-admin users
    if not _is_gestion(principal):
        # Commercial users are automatically assigned as the sales contact
        data["sales_contact_id"] = principal.id
    elif "sales_contact_id" not in data:
        # Admin creating without specifying: no auto-assignment
        pass

    client = Client(**data)
    db.add(client)
    db.commit()
    db.refresh(client)

    # Sentry logging
    sentry_sdk.capture_message(
        f"Client créé: id={client.id}, nom={client.full_name}, "
        f"par={principal.email}",
        level="info",
    )

    return client


def update_client(
    db: Session,
    principal: Principal,
    client_id: int,
    data: Dict[str, Any],
) -> Client:
    """
    Update an existing client.

    Business rules:
    - Requires 'client.write' permission.
    - Commercial users can only update clients they are responsible for.
    - Gestion users can update any client.

    Args:
        db: Database session.
        principal: The authenticated user.
        client_id: ID of the client to update.
        data: Fields to update.

    Returns:
        The updated Client object.

    Raises:
        PermissionError: If user lacks permission.
        ClientOwnershipError: If commercial tries to update someone else's client.
        ValueError: If client not found.
    """
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "client.write", perms)

    client = db.get(Client, client_id)
    if not client:
        raise ValueError(f"Client {client_id} non trouvé")

    # Check ownership for non-admin users
    _check_client_ownership(db, principal, client)

    # Prevent commercial from reassigning to another sales contact
    if "sales_contact_id" in data and not _is_gestion(principal):
        del data["sales_contact_id"]  # Ignore this field for non-admins

    # Apply updates
    for key, value in data.items():
        if hasattr(client, key):
            setattr(client, key, value)

    db.commit()
    db.refresh(client)

    # Sentry logging
    sentry_sdk.capture_message(
        f"Client mis à jour: id={client.id}, par={principal.email}",
        level="info",
    )

    return client


def get_client(db: Session, client_id: int) -> Optional[Client]:
    """
    Retrieve a client by ID.
    
    Args:
        db: Database session.
        client_id: The client ID.
        
    Returns:
        Client object or None if not found.
    """
    return db.get(Client, client_id)


def get_clients_for_user(db: Session, principal: Principal) -> list[Client]:
    """
    Get clients that a user is responsible for (as sales contact).
    
    Args:
        db: Database session.
        principal: The authenticated user.
        
    Returns:
        List of Client objects.
    """
    return db.query(Client).filter(Client.sales_contact_id == principal.id).all()
