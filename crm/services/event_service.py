"""
Services for creating and updating events.

Business rules (from specification):
- COMMERCIAL can create events for clients who have a SIGNED contract
- GESTION can create/modify any event and assign support contacts
- SUPPORT can only update events they are assigned to
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
import sentry_sdk

from ..models import Event, Contract, User
from ..principal import Principal
from ..auth import ensure_permission
from ..rbac import get_user_permissions


class EventOwnershipError(PermissionError):
    """Raised when a user tries to modify an event they don't own."""
    
    def __init__(self, event_id: int, user_email: str, role: str):
        self.event_id = event_id
        self.user_email = user_email
        self.role = role
        
        if role == "support":
            message = (
                f"Vous n'êtes pas le contact support de l'événement {event_id}. "
                f"Seul le support assigné peut modifier cet événement."
            )
        else:
            message = (
                f"Vous n'avez pas les droits pour modifier l'événement {event_id}."
            )
        super().__init__(message)


class EventCreationError(ValueError):
    """Raised when event creation fails due to business rules."""
    pass


def _ensure_authenticated(principal: Optional[Principal]) -> None:
    """Raise if no authenticated user is provided."""
    if principal is None:
        raise PermissionError("Authentification requise.")


def _is_gestion(principal: Principal) -> bool:
    """Check if the principal has the 'gestion' (admin) role."""
    return principal.role == "gestion"


def _is_commercial(principal: Principal) -> bool:
    """Check if the principal has the 'commercial' role."""
    return principal.role == "commercial"


def _is_support(principal: Principal) -> bool:
    """Check if the principal has the 'support' role."""
    return principal.role == "support"


def _check_event_ownership(
    db: Session,
    principal: Principal,
    event: Event,
) -> None:
    """
    Verify that the principal is allowed to modify this event.
    
    Rules:
    - Gestion users can modify any event
    - Support users can only modify events where they are the support_contact
    - Commercial users cannot modify events (only create)
    
    Raises:
        EventOwnershipError: If the user doesn't have permission.
    """
    if _is_gestion(principal):
        return  # Admin can modify anything
    
    if _is_support(principal):
        # Support can only modify events assigned to them
        if event.support_contact_id != principal.id:
            raise EventOwnershipError(event.id, principal.email, "support")
        return
    
    if _is_commercial(principal):
        # Commercial cannot update events (per specification)
        # They can only create events
        raise EventOwnershipError(event.id, principal.email, "commercial")
    
    # Unknown role: deny access
    raise EventOwnershipError(event.id, principal.email, principal.role or "unknown")


def _parse_event_date(data: Dict[str, Any]) -> None:
    """
    Parse and convert event_date to datetime if it's a string.
    
    Modifies the data dict in place.
    
    Raises:
        ValueError: If the date format is invalid.
    """
    if "event_date" not in data or data["event_date"] is None:
        return
    
    value = data["event_date"]
    
    if isinstance(value, datetime):
        return  # Already a datetime
    
    if isinstance(value, str):
        # The date should already be normalized by ui.validate_event_payload
        # but we handle ISO format parsing here as a fallback
        try:
            data["event_date"] = datetime.fromisoformat(value)
        except ValueError:
            raise ValueError(
                f"Format de date invalide: {value}. "
                f"Utilisez le format ISO: YYYY-MM-DDTHH:MM:SS"
            )


def create_event(
    db: Session,
    principal: Principal,
    contract_id: int,
    data: Dict[str, Any],
) -> Event:
    """
    Create a new event for a contract.

    Business rules:
    - Requires 'event.write' permission.
    - GESTION: Can create events for any contract.
    - COMMERCIAL: Can only create events for SIGNED contracts of their clients.
    - SUPPORT: Cannot create events (only update).

    Args:
        db: Database session.
        principal: The authenticated user.
        contract_id: ID of the contract for this event.
        data: Event data (event_date, location, attendees, notes, etc.).

    Returns:
        The newly created Event object.

    Raises:
        PermissionError: If user lacks permission.
        ValueError: If contract not found.
        EventCreationError: If business rules are violated.
    """
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "event.write", perms)

    # Verify contract exists
    contract = db.get(Contract, contract_id)
    if not contract:
        raise ValueError(f"Contrat {contract_id} non trouvé")

    # Support cannot create events
    if _is_support(principal):
        raise EventCreationError(
            "Les membres du support ne peuvent pas créer d'événements. "
            "Seuls les commerciaux et la gestion peuvent le faire."
        )

    # Commercial: check ownership and contract status
    if _is_commercial(principal):
        client = contract.client
        
        # Must be the sales contact for the client
        if not client or client.sales_contact_id != principal.id:
            raise EventCreationError(
                f"Vous ne pouvez créer des événements que pour les contrats "
                f"de vos propres clients."
            )
        
        # Contract must be signed
        if (contract.status or "").upper() != "SIGNED":
            raise EventCreationError(
                f"Le contrat {contract_id} n'est pas signé. "
                f"Vous ne pouvez créer un événement que pour un contrat signé."
            )

    # Parse event_date if provided as string
    _parse_event_date(data)

    event = Event(contract_id=contract_id, **data)
    db.add(event)
    db.commit()
    db.refresh(event)

    # Sentry logging
    sentry_sdk.capture_message(
        f"Événement créé: id={event.id}, contrat_id={contract_id}, "
        f"lieu={event.location}, date={event.event_date}, "
        f"par={principal.email}",
        level="info",
    )

    return event


def update_event(
    db: Session,
    principal: Principal,
    event_id: int,
    data: Dict[str, Any],
) -> Event:
    """
    Update an existing event.

    Business rules:
    - Requires 'event.write' permission.
    - GESTION: Can modify any event (including assigning support contact).
    - SUPPORT: Can only modify events assigned to them.
    - COMMERCIAL: Cannot modify events.

    Special handling:
    - 'support_email' in data will be resolved to support_contact_id.

    Args:
        db: Database session.
        principal: The authenticated user.
        event_id: ID of the event to update.
        data: Fields to update.

    Returns:
        The updated Event object.

    Raises:
        PermissionError: If user lacks permission.
        EventOwnershipError: If user tries to update an event they don't own.
        ValueError: If event not found or support user not found.
    """
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "event.write", perms)

    event = db.get(Event, event_id)
    if not event:
        raise ValueError(f"Événement {event_id} non trouvé")

    # Check ownership
    _check_event_ownership(db, principal, event)

    # Handle support_email -> support_contact_id resolution
    if "support_email" in data:
        support_email = data.pop("support_email")
        if support_email:
            support_user = db.query(User).filter(User.email == support_email).one_or_none()
            if not support_user:
                raise ValueError(f"Collaborateur support non trouvé: {support_email}")
            
            # Only gestion can assign support contact
            if not _is_gestion(principal):
                raise PermissionError(
                    "Seule l'équipe de gestion peut assigner un contact support."
                )
            
            data["support_contact_id"] = support_user.id

    # Support cannot reassign the support contact
    if "support_contact_id" in data and _is_support(principal):
        del data["support_contact_id"]

    # Parse event_date if provided as string
    _parse_event_date(data)

    # Apply updates
    for key, value in data.items():
        if hasattr(event, key):
            setattr(event, key, value)

    db.commit()
    db.refresh(event)

    # Sentry logging
    sentry_sdk.capture_message(
        f"Événement mis à jour: id={event.id}, par={principal.email}",
        level="info",
    )

    return event


def get_event(db: Session, event_id: int) -> Optional[Event]:
    """
    Retrieve an event by ID.
    
    Args:
        db: Database session.
        event_id: The event ID.
        
    Returns:
        Event object or None if not found.
    """
    return db.get(Event, event_id)


def get_events_without_support(db: Session) -> list[Event]:
    """
    Get all events without an assigned support contact.
    
    Returns:
        List of Event objects without support_contact_id.
    """
    return db.query(Event).filter(Event.support_contact_id.is_(None)).all()


def get_events_for_support(db: Session, support_user_id: int) -> list[Event]:
    """
    Get all events assigned to a specific support user.
    
    Args:
        db: Database session.
        support_user_id: The support user's ID.
        
    Returns:
        List of Event objects.
    """
    return db.query(Event).filter(Event.support_contact_id == support_user_id).all()


def get_events_for_contract(db: Session, contract_id: int) -> list[Event]:
    """
    Get all events for a specific contract.
    
    Args:
        db: Database session.
        contract_id: The contract ID.
        
    Returns:
        List of Event objects.
    """
    return db.query(Event).filter(Event.contract_id == contract_id).all()


def assign_support_contact(
    db: Session,
    principal: Principal,
    event_id: int,
    support_user_id: int,
) -> Event:
    """
    Assign a support contact to an event.
    
    Only gestion users can perform this action.
    
    Args:
        db: Database session.
        principal: The authenticated user (must be gestion).
        event_id: The event ID.
        support_user_id: The support user's ID.
        
    Returns:
        The updated Event object.
        
    Raises:
        PermissionError: If user is not gestion.
        ValueError: If event or user not found.
    """
    _ensure_authenticated(principal)
    
    if not _is_gestion(principal):
        raise PermissionError(
            "Seule l'équipe de gestion peut assigner un contact support."
        )
    
    event = db.get(Event, event_id)
    if not event:
        raise ValueError(f"Événement {event_id} non trouvé")
    
    support_user = db.get(User, support_user_id)
    if not support_user:
        raise ValueError(f"Collaborateur {support_user_id} non trouvé")
    
    # Optionally verify the user has support role
    if support_user.role and support_user.role.name != "support":
        # Warning but don't block - maybe they want to assign someone else
        sentry_sdk.capture_message(
            f"Attention: assignation d'un non-support ({support_user.email}) "
            f"à l'événement {event_id}",
            level="warning",
        )
    
    event.support_contact_id = support_user_id
    db.commit()
    db.refresh(event)
    
    sentry_sdk.capture_message(
        f"Support assigné: événement={event_id}, support={support_user.email}, "
        f"par={principal.email}",
        level="info",
    )
    
    return event