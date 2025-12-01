"""
Read-only services for business entities (clients, contracts, events).

These services provide read access to all authenticated users,
as specified in the requirements (cahier des charges):
"Tous les collaborateurs doivent pouvoir accéder à tous les clients,
contrats et événements en lecture seule."
"""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session

from ..models import Client, Contract, Event
from ..principal import Principal
from ..exceptions import NotAuthenticatedError


def _ensure_authenticated(principal: Optional[Principal]) -> None:
    """
    Verify that a principal is provided.
    
    Raises:
        NotAuthenticatedError: If principal is None.
    """
    if principal is None:
        raise NotAuthenticatedError()


# =============================================================================
# CLIENT READ OPERATIONS
# =============================================================================

def list_clients(db: Session, principal: Principal) -> List[Client]:
    """
    Return all clients.

    Access:
        Any authenticated user (gestion, commercial, support) can read all clients.

    Args:
        db: Database session.
        principal: The authenticated user.

    Returns:
        List of all Client objects, ordered by ID.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return db.query(Client).order_by(Client.id).all()


def get_client_by_id(db: Session, principal: Principal, client_id: int) -> Optional[Client]:
    """
    Return a single client by ID.

    Args:
        db: Database session.
        principal: The authenticated user.
        client_id: The client's ID.

    Returns:
        Client object or None if not found.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return db.get(Client, client_id)


def list_clients_for_commercial(db: Session, principal: Principal) -> List[Client]:
    """
    Return clients assigned to the current user (as sales contact).

    Useful for commercial users to see only their portfolio.

    Args:
        db: Database session.
        principal: The authenticated user.

    Returns:
        List of Client objects where principal is the sales contact.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return (
        db.query(Client)
        .filter(Client.sales_contact_id == principal.id)
        .order_by(Client.id)
        .all()
    )


# =============================================================================
# CONTRACT READ OPERATIONS
# =============================================================================

def list_contracts(db: Session, principal: Principal) -> List[Contract]:
    """
    Return all contracts.

    Access:
        Any authenticated user can read all contracts.

    Args:
        db: Database session.
        principal: The authenticated user.

    Returns:
        List of all Contract objects, ordered by ID.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return db.query(Contract).order_by(Contract.id).all()


def get_contract_by_id(db: Session, principal: Principal, contract_id: int) -> Optional[Contract]:
    """
    Return a single contract by ID.

    Args:
        db: Database session.
        principal: The authenticated user.
        contract_id: The contract's ID.

    Returns:
        Contract object or None if not found.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return db.get(Contract, contract_id)


def list_contracts_unsigned(db: Session, principal: Principal) -> List[Contract]:
    """
    Return contracts that are not yet signed.

    Useful for commercial team to filter pending contracts.

    Args:
        db: Database session.
        principal: The authenticated user.

    Returns:
        List of Contract objects with status != 'SIGNED'.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return (
        db.query(Contract)
        .filter(Contract.status != "SIGNED")
        .order_by(Contract.id)
        .all()
    )


def list_contracts_unpaid(db: Session, principal: Principal) -> List[Contract]:
    """
    Return contracts with remaining balance (amount_due > 0).

    Useful for commercial team to track unpaid contracts.

    Args:
        db: Database session.
        principal: The authenticated user.

    Returns:
        List of Contract objects with amount_due > 0.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return (
        db.query(Contract)
        .filter(Contract.amount_due > 0)
        .order_by(Contract.id)
        .all()
    )


def list_contracts_for_commercial(db: Session, principal: Principal) -> List[Contract]:
    """
    Return contracts where the current user is the sales contact.

    Args:
        db: Database session.
        principal: The authenticated user.

    Returns:
        List of Contract objects assigned to the principal.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return (
        db.query(Contract)
        .filter(Contract.sales_contact_id == principal.id)
        .order_by(Contract.id)
        .all()
    )


# =============================================================================
# EVENT READ OPERATIONS
# =============================================================================

def list_events(db: Session, principal: Principal) -> List[Event]:
    """
    Return all events.

    Access:
        Any authenticated user can read all events.

    Args:
        db: Database session.
        principal: The authenticated user.

    Returns:
        List of all Event objects, ordered by ID.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return db.query(Event).order_by(Event.id).all()


def get_event_by_id(db: Session, principal: Principal, event_id: int) -> Optional[Event]:
    """
    Return a single event by ID.

    Args:
        db: Database session.
        principal: The authenticated user.
        event_id: The event's ID.

    Returns:
        Event object or None if not found.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return db.get(Event, event_id)


def list_events_without_support(db: Session, principal: Principal) -> List[Event]:
    """
    Return events that don't have a support contact assigned.

    Useful for gestion team to identify events needing assignment.

    Args:
        db: Database session.
        principal: The authenticated user.

    Returns:
        List of Event objects without support_contact_id.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return (
        db.query(Event)
        .filter(Event.support_contact_id.is_(None))
        .order_by(Event.id)
        .all()
    )


def list_events_for_support(db: Session, principal: Principal) -> List[Event]:
    """
    Return events assigned to the current user (as support contact).

    Useful for support team to see only their events.

    Args:
        db: Database session.
        principal: The authenticated user.

    Returns:
        List of Event objects where principal is the support contact.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return (
        db.query(Event)
        .filter(Event.support_contact_id == principal.id)
        .order_by(Event.id)
        .all()
    )


def list_events_by_date(db: Session, principal: Principal) -> List[Event]:
    """
    Return all events ordered by event date (soonest first).

    Args:
        db: Database session.
        principal: The authenticated user.

    Returns:
        List of Event objects ordered by event_date.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    _ensure_authenticated(principal)
    return (
        db.query(Event)
        .order_by(Event.event_date.asc())
        .all()
    )