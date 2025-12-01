"""
Services for creating and updating contracts.

Business rules (from specification):
- GESTION can create and modify ALL contracts
- COMMERCIAL can modify contracts of clients they are responsible for
- Contract creation requires a valid client
- Sentry logs contract creation and signature
"""

from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
import sentry_sdk

from ..models import Contract, Client
from ..principal import Principal
from ..auth import ensure_permission
from ..rbac import get_user_permissions


class ContractOwnershipError(PermissionError):
    """Raised when a user tries to modify a contract they don't own."""
    
    def __init__(self, contract_id: int, user_email: str):
        self.contract_id = contract_id
        self.user_email = user_email
        super().__init__(
            f"Vous n'êtes pas le commercial responsable du contrat {contract_id}. "
            f"Seul le commercial du client associé peut modifier ce contrat."
        )


class ContractCreationError(ValueError):
    """Raised when contract creation fails due to business rules."""
    pass


def _ensure_authenticated(principal: Optional[Principal]) -> None:
    """Raise if no authenticated user is provided."""
    if principal is None:
        raise PermissionError("Authentification requise.")


def _is_gestion(principal: Principal) -> bool:
    """Check if the principal has the 'gestion' (admin) role."""
    return principal.role == "gestion"


def _check_contract_ownership(
    db: Session,
    principal: Principal,
    contract: Contract,
) -> None:
    """
    Verify that the principal is allowed to modify this contract.
    
    Rules:
    - Gestion users can modify any contract
    - Commercial users can only modify contracts where:
      - They are the sales_contact on the contract, OR
      - They are the sales_contact on the associated client
    
    Raises:
        ContractOwnershipError: If the user doesn't have permission.
    """
    if _is_gestion(principal):
        return  # Admin can modify anything
    
    # Check if user is the sales contact on the contract
    if contract.sales_contact_id == principal.id:
        return
    
    # Check if user is the sales contact on the client
    client = contract.client
    if client and client.sales_contact_id == principal.id:
        return
    
    raise ContractOwnershipError(contract.id, principal.email)


def create_contract(
    db: Session,
    principal: Principal,
    client_id: int,
    data: Dict[str, Any],
) -> Contract:
    """
    Create a new contract for a given client.

    Business rules:
    - Requires 'contract.write' permission.
    - GESTION: Can create contracts for any client.
    - COMMERCIAL: Can create contracts for their own clients only.
    - The sales_contact on the contract is set to the client's sales_contact.

    Args:
        db: Database session.
        principal: The authenticated user.
        client_id: ID of the client for this contract.
        data: Contract data (total_amount, amount_due, status).

    Returns:
        The newly created Contract object.

    Raises:
        PermissionError: If user lacks permission.
        ValueError: If client not found.
        ContractCreationError: If business rules are violated.
    """
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "contract.write", perms)

    # Verify client exists
    client = db.get(Client, client_id)
    if not client:
        raise ValueError(f"Client {client_id} non trouvé")

    # Commercial can only create contracts for their own clients
    if not _is_gestion(principal):
        if client.sales_contact_id != principal.id:
            raise ContractCreationError(
                f"Vous ne pouvez créer des contrats que pour vos propres clients. "
                f"Le client {client_id} n'est pas dans votre portefeuille."
            )

    # Set the sales contact to the client's sales contact
    # (or to the principal if they are the sales contact)
    sales_contact_id = client.sales_contact_id or principal.id

    contract = Contract(
        client_id=client_id,
        sales_contact_id=sales_contact_id,
        **data
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)

    # Sentry logging
    sentry_sdk.capture_message(
        f"Contrat créé: id={contract.id}, client_id={client_id}, "
        f"montant={contract.total_amount}, statut={contract.status}, "
        f"par={principal.email}",
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

    Business rules:
    - Requires 'contract.write' permission.
    - GESTION: Can modify any contract.
    - COMMERCIAL: Can only modify contracts for their own clients.
    - When status changes to SIGNED, signed_at is set automatically.

    Args:
        db: Database session.
        principal: The authenticated user.
        contract_id: ID of the contract to update.
        data: Fields to update.

    Returns:
        The updated Contract object.

    Raises:
        PermissionError: If user lacks permission.
        ContractOwnershipError: If commercial tries to update someone else's contract.
        ValueError: If contract not found.
    """
    _ensure_authenticated(principal)

    perms = get_user_permissions(db, principal)
    ensure_permission(principal, "contract.write", perms)

    contract = db.get(Contract, contract_id)
    if not contract:
        raise ValueError(f"Contrat {contract_id} non trouvé")

    # Check ownership
    _check_contract_ownership(db, principal, contract)

    old_status = contract.status

    # Apply updates
    for key, value in data.items():
        if hasattr(contract, key):
            setattr(contract, key, value)

    # Auto-set signed_at when contract is signed
    new_status = (contract.status or "").upper()
    if old_status != "SIGNED" and new_status == "SIGNED":
        contract.signed_at = datetime.utcnow()
        
        # Sentry logging for signature
        sentry_sdk.capture_message(
            f"Contrat signé: id={contract_id}, client_id={contract.client_id}, "
            f"par={principal.email}",
            level="info",
        )

    db.commit()
    db.refresh(contract)

    # General update logging
    sentry_sdk.capture_message(
        f"Contrat mis à jour: id={contract.id}, par={principal.email}",
        level="info",
    )

    return contract


def get_contract(db: Session, contract_id: int) -> Optional[Contract]:
    """
    Retrieve a contract by ID.
    
    Args:
        db: Database session.
        contract_id: The contract ID.
        
    Returns:
        Contract object or None if not found.
    """
    return db.get(Contract, contract_id)


def get_unsigned_contracts(db: Session) -> list[Contract]:
    """
    Get all contracts that are not signed.
    
    Returns:
        List of unsigned Contract objects.
    """
    return db.query(Contract).filter(Contract.status != "SIGNED").all()


def get_unpaid_contracts(db: Session) -> list[Contract]:
    """
    Get all contracts with remaining balance.
    
    Returns:
        List of Contract objects with amount_due > 0.
    """
    return db.query(Contract).filter(Contract.amount_due > 0).all()


def get_contracts_for_client(db: Session, client_id: int) -> list[Contract]:
    """
    Get all contracts for a specific client.
    
    Args:
        db: Database session.
        client_id: The client ID.
        
    Returns:
        List of Contract objects.
    """
    return db.query(Contract).filter(Contract.client_id == client_id).all()