"""User interface helpers (display & validation) for the CLI."""

from __future__ import annotations

from typing import Iterable, Dict, Any

from rich.console import Console
from rich.table import Table


console = Console()


# ============================================================
# DISPLAY HELPERS
# ============================================================

def print_clients_table(clients: Iterable[Any]) -> None:
    """Display a list of clients in a nice table."""
    table = Table(title="Clients")

    table.add_column("ID", justify="right")
    table.add_column("Full name")
    table.add_column("Email")
    table.add_column("Company")
    table.add_column("Phone")
    table.add_column("Mobile")

    for c in clients:
        table.add_row(
            str(c.id),
            c.full_name or "",
            c.email or "",
            getattr(c, "company", "") or "",
            getattr(c, "phone", "") or "",
            getattr(c, "mobile", "") or "",
        )

    console.print(table)


def print_contracts_table(contracts: Iterable[Any]) -> None:
    """Display a list of contracts in a nice table."""
    table = Table(title="Contracts")

    table.add_column("ID", justify="right")
    table.add_column("Client ID", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Due", justify="right")
    table.add_column("Status")

    for ct in contracts:
        table.add_row(
            str(ct.id),
            str(ct.client_id),
            f"{ct.total_amount:.2f}",
            f"{ct.amount_due:.2f}",
            ct.status or "",
        )

    console.print(table)


def print_events_table(events: Iterable[Any]) -> None:
    """Display a list of events in a nice table."""
    table = Table(title="Events")

    table.add_column("ID", justify="right")
    table.add_column("Contract ID", justify="right")
    table.add_column("Date")
    table.add_column("Location")
    table.add_column("Attendees", justify="right")
    table.add_column("Support ID", justify="right")

    for ev in events:
        table.add_row(
            str(ev.id),
            str(ev.contract_id),
            str(ev.event_date),
            ev.location or "",
            str(ev.attendees or ""),
            str(ev.support_contact_id or ""),
        )

    console.print(table)


# ============================================================
# VALIDATION HELPERS
# ============================================================

def _ensure_keys(payload: Dict[str, Any], required_keys: list[str]) -> None:
    missing = [k for k in required_keys if k not in payload]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")


def validate_client_payload(payload: Dict[str, Any]) -> None:
    """Basic validation for client create/update."""
    _ensure_keys(payload, ["full_name", "email"])

    email = payload.get("email", "")
    if "@" not in email:
        raise ValueError("Invalid email address")

    # Optional but if present, must be strings
    for key in ["company", "phone", "mobile"]:
        if key in payload and payload[key] is not None and not isinstance(payload[key], str):
            raise ValueError(f"{key} must be a string")


def validate_contract_payload(payload: Dict[str, Any]) -> None:
    """Basic validation for contract create/update."""
    _ensure_keys(payload, ["total_amount", "amount_due", "status"])

    try:
        total = float(payload["total_amount"])
        due = float(payload["amount_due"])
    except (TypeError, ValueError):
        raise ValueError("total_amount and amount_due must be numbers")

    if total < 0 or due < 0:
        raise ValueError("Amounts cannot be negative")

    status = str(payload["status"]).upper()
    if status not in {"PENDING", "SIGNED", "CANCELLED"}:
        raise ValueError("status must be one of: PENDING, SIGNED, CANCELLED")
    payload["status"] = status  # normalisation


def validate_event_payload(payload: Dict[str, Any]) -> None:
    """Basic validation for event create/update."""
    _ensure_keys(payload, ["event_date", "location", "attendees"])

    # event_date is string here, conversion en datetime est faite dans event_service
    if not isinstance(payload["event_date"], str):
        raise ValueError("event_date must be a string (ISO format)")

    if not isinstance(payload["location"], str):
        raise ValueError("location must be a string")

    try:
        attendees = int(payload["attendees"])
    except (TypeError, ValueError):
        raise ValueError("attendees must be an integer")

    if attendees < 0:
        raise ValueError("attendees cannot be negative")
    payload["attendees"] = attendees
