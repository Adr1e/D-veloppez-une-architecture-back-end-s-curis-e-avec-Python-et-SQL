"""Read-only services for business entities (clients, contracts, events)."""

from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session

from ..models import Client, Contract, Event
from ..principal import Principal


def _ensure_authenticated(principal: Principal) -> None:
    """Raise if no authenticated user is provided."""
    if principal is None:
        # Ici on pourrait utiliser un type d'erreur dédié si besoin
        raise PermissionError("Authentication required to access data.")


def list_clients(db: Session, principal: Principal) -> List[Client]:
    """
    Return all clients.

    Notes:
        - Any authenticated user (gestion, commercial, support) can read clients.
        - No filtering by role: le cahier des charges impose la lecture pour tous.
    """
    _ensure_authenticated(principal)
    return db.query(Client).all()


def list_contracts(db: Session, principal: Principal) -> List[Contract]:
    """
    Return all contracts.

    Notes:
        - Any authenticated user can read all contracts (lecture seule).
    """
    _ensure_authenticated(principal)
    return db.query(Contract).all()


def list_events(db: Session, principal: Principal) -> List[Event]:
    """
    Return all events.

    Notes:
        - Any authenticated user can read all events (lecture seule).
    """
    _ensure_authenticated(principal)
    return db.query(Event).all()
