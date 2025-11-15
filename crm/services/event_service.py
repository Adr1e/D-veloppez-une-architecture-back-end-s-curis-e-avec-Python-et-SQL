"""Services for creating and updating events."""

from __future__ import annotations

from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime


from ..models import Event, Contract
from ..principal import Principal
from ..auth import ensure_permission
from ..rbac import get_user_permissions


def _ensure_authenticated(principal: Principal) -> None:
    if principal is None:
        raise PermissionError("Authentication required.")



def create_event(db: Session, principal: Principal, contract_id: int, data: Dict[str, Any]) -> Event:
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "event.write", perms)

    contract = db.get(Contract, contract_id)
    if not contract:
        raise ValueError(f"Contract {contract_id} not found")

    # Convert event_date if provided as string
    if "event_date" in data and isinstance(data["event_date"], str):
        try:
            data["event_date"] = datetime.fromisoformat(data["event_date"])
        except ValueError:
            raise ValueError("event_date must be ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")

    event = Event(contract_id=contract_id, **data)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event



def update_event(
    db: Session,
    principal: Principal,
    event_id: int,
    data: Dict[str, Any],
) -> Event:
    """
    Update an existing event.

    Notes:
        - Requires 'event.write' permission.
        - All provided fields in 'data' are applied if they exist on the model.
    """
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "event.write", perms)

    event = db.get(Event, event_id)
    if not event:
        raise ValueError(f"Event {event_id} not found")

    for key, value in data.items():
        if hasattr(event, key):
            setattr(event, key, value)

    db.commit()
    db.refresh(event)
    return event
