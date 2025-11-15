"""Services for creating and updating contracts."""

from __future__ import annotations

from typing import Dict, Any

from sqlalchemy.orm import Session
import sentry_sdk

from ..models import Contract, Client
from ..principal import Principal
from ..auth import ensure_permission
from ..rbac import get_user_permissions


def _ensure_authenticated(principal: Principal) -> None:
    if principal is None:
        raise PermissionError("Authentication required.")


def create_contract(
    db: Session,
    principal: Principal,
    client_id: int,
    data: Dict[str, Any],
) -> Contract:
    """
    Create a new contract for the given client.

    Notes:
        - Requires 'contract.write' permission.
        - 'data' is a dict of fields passed to the Contract constructor.
          Example:
            {
                "total_amount": 1000.0,
                "amount_due": 1000.0,
                "status": "PENDING"
            }
    """
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "contract.write", perms)

    client = db.get(Client, client_id)
    if not client:
        raise ValueError(f"Client {client_id} not found")

    contract = Contract(client_id=client_id, **data)
    db.add(contract)
    db.commit()
    db.refresh(contract)

    # Journalisation Sentry (création de contrat – bonus)
    sentry_sdk.capture_message(
        f"Contract created: id={contract.id}, client_id={client_id}, status={contract.status}",
        level="info",
    )

    return contract


def update_contract(
    db: Session,
    principal: Principal,
    contract_id: int,
    data: Dict[str, Any],
) -> Contract:
    """
    Update an existing contract.

    Notes:
        - Requires 'contract.write' permission.
        - All provided fields in 'data' are applied if they exist on the model.
    """
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "contract.write", perms)

    contract = db.get(Contract, contract_id)
    if not contract:
        raise ValueError(f"Contract {contract_id} not found")

    old_status = contract.status

    for key, value in data.items():
        # On ne touche qu’aux champs qui existent vraiment sur le modèle
        if hasattr(contract, key):
            setattr(contract, key, value)

    db.commit()
    db.refresh(contract)

    # Journalisation Sentry : signature de contrat
    if old_status != "SIGNED" and contract.status == "SIGNED":
        sentry_sdk.capture_message(
            f"Contract {contract_id} signed",
            level="info",
        )

    return contract
