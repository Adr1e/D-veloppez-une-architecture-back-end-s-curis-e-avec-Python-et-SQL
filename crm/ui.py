"""
User interface helpers (display and validation) for the CLI.

This module provides:
- Table display functions for all entities
- Payload validation before database operations
- Date parsing and conversion (FR format to ISO)
- Custom exceptions for better error handling
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable, Dict, Any, Optional

from rich.console import Console
from rich.table import Table

console = Console()


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================


class ValidationError(Exception):
    """Raised when payload validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.field:
            return f"[{self.field}] {self.message}"
        return self.message


class DateParseError(ValidationError):
    """Raised when date parsing fails."""
    
    def __init__(self, value: str, expected_formats: list[str]):
        self.value = value
        self.expected_formats = expected_formats
        message = (
            f"Unable to parse date '{value}'. "
            f"Expected formats: {', '.join(expected_formats)}"
        )
        super().__init__(message, field="date")


# ============================================================
# DATE PARSING AND CONVERSION
# ============================================================

# Supported date formats for parsing user input
DATE_FORMATS = [
    # ISO formats (preferred)
    "%Y-%m-%dT%H:%M:%S",      # 2025-06-01T10:00:00
    "%Y-%m-%dT%H:%M",         # 2025-06-01T10:00
    "%Y-%m-%d %H:%M:%S",      # 2025-06-01 10:00:00
    "%Y-%m-%d %H:%M",         # 2025-06-01 10:00
    "%Y-%m-%d",               # 2025-06-01
    
    # French formats (DD/MM/YYYY)
    "%d/%m/%Y %H:%M:%S",      # 01/06/2025 10:00:00
    "%d/%m/%Y %H:%M",         # 01/06/2025 10:00
    "%d/%m/%Y %Hh%M",         # 01/06/2025 10h00
    "%d/%m/%Y",               # 01/06/2025
    
    # French formats with dashes
    "%d-%m-%Y %H:%M:%S",      # 01-06-2025 10:00:00
    "%d-%m-%Y %H:%M",         # 01-06-2025 10:00
    "%d-%m-%Y",               # 01-06-2025
    
    # French text formats
    "%d %B %Y",               # 01 juin 2025 (requires locale)
    "%d %b %Y",               # 01 jun 2025
]

# French month names for manual parsing
FRENCH_MONTHS = {
    "janvier": 1, "jan": 1, "janv": 1,
    "février": 2, "fevrier": 2, "fév": 2, "fev": 2,
    "mars": 3, "mar": 3,
    "avril": 4, "avr": 4,
    "mai": 5,
    "juin": 6, "jun": 6,
    "juillet": 7, "juil": 7, "jul": 7,
    "août": 8, "aout": 8, "aoû": 8,
    "septembre": 9, "sept": 9, "sep": 9,
    "octobre": 10, "oct": 10,
    "novembre": 11, "nov": 11,
    "décembre": 12, "decembre": 12, "déc": 12, "dec": 12,
}


def _parse_french_text_date(text: str) -> Optional[datetime]:
    """
    Try to parse a French text date like '18 avril 2021' or '29 mars 2023'.
    
    Returns:
        datetime object if parsing succeeds, None otherwise.
    """
    text = text.lower().strip()
    
    # Pattern: day month year [time]
    # Examples: "18 avril 2021", "29 mars 2023 14h30", "5 jun 2023 @ 1PM"
    
    # Remove common separators
    text = text.replace("@", " ").replace(",", " ")
    
    # Try to match: DD MONTH YYYY [HH:MM or HHhMM or HHPM/AM]
    pattern = r"(\d{1,2})\s+([a-zéûô]+)\s+(\d{4})(?:\s+(\d{1,2})[h:]?(\d{2})?\s*(am|pm)?)?"
    match = re.match(pattern, text, re.IGNORECASE)
    
    if not match:
        return None
    
    day = int(match.group(1))
    month_str = match.group(2).lower()
    year = int(match.group(3))
    hour = int(match.group(4)) if match.group(4) else 0
    minute = int(match.group(5)) if match.group(5) else 0
    am_pm = match.group(6).lower() if match.group(6) else None
    
    # Convert month name to number
    month = FRENCH_MONTHS.get(month_str)
    if month is None:
        return None
    
    # Handle AM/PM
    if am_pm == "pm" and hour < 12:
        hour += 12
    elif am_pm == "am" and hour == 12:
        hour = 0
    
    try:
        return datetime(year, month, day, hour, minute)
    except ValueError:
        return None


def parse_date(value: str) -> datetime:
    """
    Parse a date string in various formats (ISO or French) and return a datetime.
    
    Supported formats:
    - ISO: 2025-06-01, 2025-06-01T10:00:00, 2025-06-01 10:00
    - French: 01/06/2025, 01/06/2025 10:00, 01/06/2025 10h00
    - French text: 18 avril 2021, 29 mars 2023
    
    Args:
        value: The date string to parse.
        
    Returns:
        A datetime object.
        
    Raises:
        DateParseError: If the date cannot be parsed.
    """
    if not isinstance(value, str):
        raise DateParseError(str(value), ["YYYY-MM-DD", "DD/MM/YYYY"])
    
    value = value.strip()
    
    if not value:
        raise DateParseError(value, ["YYYY-MM-DD", "DD/MM/YYYY"])
    
    # Try standard formats first
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    
    # Try French text date parsing
    result = _parse_french_text_date(value)
    if result is not None:
        return result
    
    # Nothing worked
    raise DateParseError(
        value, 
        ["YYYY-MM-DD", "YYYY-MM-DDTHH:MM:SS", "DD/MM/YYYY", "DD/MM/YYYY HH:MM", "18 avril 2021"]
    )


def format_date_to_iso(value: str) -> str:
    """
    Convert any supported date format to ISO format string.
    
    Args:
        value: The date string to convert.
        
    Returns:
        ISO formatted date string (YYYY-MM-DDTHH:MM:SS).
        
    Raises:
        DateParseError: If the date cannot be parsed.
    """
    dt = parse_date(value)
    return dt.isoformat()


def normalize_date_in_payload(payload: Dict[str, Any], field: str) -> None:
    """
    Normalize a date field in a payload to ISO format.
    
    This function modifies the payload in place.
    
    Args:
        payload: The data dictionary.
        field: The field name containing the date.
        
    Raises:
        DateParseError: If the date cannot be parsed.
    """
    if field in payload and payload[field] is not None:
        value = payload[field]
        if isinstance(value, str):
            payload[field] = format_date_to_iso(value)
        elif isinstance(value, datetime):
            payload[field] = value.isoformat()


# ============================================================
# DISPLAY HELPERS
# ============================================================


def _format_datetime_display(value: Any) -> str:
    """
    Format a datetime-like value as a user-friendly string for display.
    
    Converts to DD/MM/YYYY HH:MM format for French users.
    """
    if value is None:
        return ""
    
    # If it's already a datetime object
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    
    text = str(value)
    
    # Try to parse and reformat
    try:
        dt = parse_date(text)
        return dt.strftime("%d/%m/%Y %H:%M")
    except (DateParseError, ValueError):
        pass
    
    # Fallback: extract date part from ISO string
    if "T" in text:
        text = text.replace("T", " ")
    
    # Try to convert YYYY-MM-DD to DD/MM/YYYY
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        parts = text.split(" ")
        date_part = parts[0]
        time_part = parts[1] if len(parts) > 1 else ""
        
        try:
            year, month, day = date_part.split("-")
            formatted = f"{day}/{month}/{year}"
            if time_part:
                # Keep only HH:MM
                time_short = time_part[:5] if len(time_part) >= 5 else time_part
                formatted += f" {time_short}"
            return formatted
        except ValueError:
            pass
    
    return text


def print_users_table(users: Iterable[Any]) -> None:
    """
    Display a list of collaborators (users) in a table.

    Passwords are never shown for security reasons.
    """
    table = Table(title="Collaborateurs", expand=True)

    table.add_column("ID", justify="right")
    table.add_column("Email", overflow="fold")
    table.add_column("Nom complet", overflow="fold")
    table.add_column("Rôle", overflow="fold")

    for u in users:
        role_name = u.role.name if getattr(u, "role", None) is not None else ""

        table.add_row(
            str(u.id),
            u.email or "",
            u.full_name or "",
            role_name,
        )

    console.print(table)


def print_clients_table(clients: Iterable[Any]) -> None:
    """
    Display a list of clients in a table.
    """
    table = Table(title="Clients", expand=True)

    table.add_column("ID", justify="right")
    table.add_column("Nom complet", overflow="fold")
    table.add_column("Email", overflow="fold")
    table.add_column("Entreprise", overflow="fold")
    table.add_column("Téléphone", overflow="fold")
    table.add_column("Commercial", overflow="fold")
    table.add_column("Créé le", overflow="fold")
    table.add_column("Modifié le", overflow="fold")

    for c in clients:
        sales_contact = getattr(c, "sales_contact", None)
        sales_email = sales_contact.email if sales_contact is not None else ""

        table.add_row(
            str(c.id),
            c.full_name or "",
            c.email or "",
            getattr(c, "company", "") or "",
            getattr(c, "phone", "") or "",
            sales_email,
            _format_datetime_display(getattr(c, "created_at", None)),
            _format_datetime_display(getattr(c, "updated_at", None)),
        )

    console.print(table)


def print_contracts_table(contracts: Iterable[Any]) -> None:
    """
    Display a list of contracts in a table.
    """
    table = Table(title="Contrats", expand=True)

    table.add_column("ID", justify="right")
    table.add_column("Client", overflow="fold")
    table.add_column("Commercial", overflow="fold")
    table.add_column("Total", justify="right")
    table.add_column("Reste dû", justify="right")
    table.add_column("Statut", overflow="fold")
    table.add_column("Créé le", overflow="fold")
    table.add_column("Signé le", overflow="fold")

    for ct in contracts:
        client = getattr(ct, "client", None)
        client_name = client.full_name if client is not None else ""
        sales_contact = getattr(ct, "sales_contact", None)
        sales_email = sales_contact.email if sales_contact is not None else ""

        table.add_row(
            str(ct.id),
            client_name,
            sales_email,
            f"{ct.total_amount:.2f} €",
            f"{ct.amount_due:.2f} €",
            ct.status or "",
            _format_datetime_display(getattr(ct, "created_at", None)),
            _format_datetime_display(getattr(ct, "signed_at", None)),
        )

    console.print(table)


def print_events_table(events: Iterable[Any]) -> None:
    """
    Display a list of events in a table.
    """
    table = Table(title="Événements", expand=True)

    table.add_column("ID", justify="right")
    table.add_column("Contrat ID", justify="right")
    table.add_column("Nom client", overflow="fold")
    table.add_column("Email client", overflow="fold")
    table.add_column("Tél. client", overflow="fold")
    table.add_column("Date", overflow="fold")
    table.add_column("Lieu", overflow="fold")
    table.add_column("Participants", justify="right")
    table.add_column("Support", overflow="fold")
    table.add_column("Notes", overflow="fold")

    for ev in events:
        contract = getattr(ev, "contract", None)
        client = getattr(contract, "client", None) if contract else None
        client_name = client.full_name if client is not None else ""
        client_email = client.email if client is not None else ""
        client_phone = getattr(client, "phone", "") if client is not None else ""
        support = getattr(ev, "support_contact", None)
        support_email = support.email if support is not None else "[non assigné]"

        table.add_row(
            str(ev.id),
            str(ev.contract_id),
            client_name,
            client_email,
            client_phone or "",
            _format_datetime_display(getattr(ev, "event_date", None)),
            ev.location or "",
            str(ev.attendees or ""),
            support_email,
            (ev.notes or "")[:50] + "..." if ev.notes and len(ev.notes) > 50 else (ev.notes or ""),
        )

    console.print(table)


# ============================================================
# VALIDATION HELPERS
# ============================================================


def _ensure_keys(payload: Dict[str, Any], required_keys: list[str], entity: str = "entity") -> None:
    """
    Ensure that all required keys are present in the payload.
    
    Raises:
        ValidationError: When one or more keys are missing.
    """
    missing = [k for k in required_keys if k not in payload or payload[k] is None]
    if missing:
        raise ValidationError(
            f"Champ(s) requis manquant(s) pour {entity}: {', '.join(missing)}"
        )

def _validate_phone(phone: str, field_name: str = "phone") -> None:
    """
    Validate a phone number format (basic check).
    
    Raises:
        ValidationError: If the phone format is invalid.
    """
    if not phone:
        return  # Optional field
    
    # Remove spaces and common separators
    cleaned = re.sub(r"[\s.\-()]", "", phone)
    
    # Should contain only digits, possibly starting with +
    if not re.match(r"^\+?\d{6,15}$", cleaned):
        raise ValidationError(
            f"Format de téléphone invalide pour {field_name}: {phone}",
            field=field_name
        )


def validate_client_payload(payload: Dict[str, Any], is_update: bool = False) -> None:
    """
    Validate client create or update payload.
    
    Args:
        payload: The data dictionary to validate.
        is_update: If True, required fields are not enforced.
        
    Raises:
        ValidationError: If validation fails.
    """
    if not is_update:
        _ensure_keys(payload, ["full_name", "email"], entity="client")
    
    # Validate phone numbers if provided
    if "phone" in payload and payload["phone"]:
        _validate_phone(payload["phone"], "phone")
    

    
    # Validate string fields
    for key in ["full_name", "company", "phone"]:
        if key in payload and payload[key] is not None:
            if not isinstance(payload[key], str):
                raise ValidationError(f"{key} doit être une chaîne de caractères", field=key)


def validate_contract_payload(payload: Dict[str, Any], is_update: bool = False) -> None:
    """
    Validate contract create or update payload.
    
    Args:
        payload: The data dictionary to validate.
        is_update: If True, required fields are not enforced.
        
    Raises:
        ValidationError: If validation fails.
    """
    if not is_update:
        _ensure_keys(payload, ["total_amount", "amount_due", "status"], entity="contrat")
    
    # Validate amounts
    for field in ["total_amount", "amount_due"]:
        if field in payload and payload[field] is not None:
            try:
                value = float(payload[field])
                if value < 0:
                    raise ValidationError(
                        f"{field} ne peut pas être négatif",
                        field=field
                    )
                payload[field] = value  # Normalize to float
            except (TypeError, ValueError):
                raise ValidationError(
                    f"{field} doit être un nombre",
                    field=field
                )
    
    # Validate status
    valid_statuses = {"PENDING", "SIGNED", "CANCELLED"}
    if "status" in payload and payload["status"] is not None:
        status = str(payload["status"]).upper().strip()
        if status not in valid_statuses:
            raise ValidationError(
                f"Statut invalide: {payload['status']}. "
                f"Valeurs acceptées: {', '.join(valid_statuses)}",
                field="status"
            )
        payload["status"] = status  # Normalize to uppercase


def validate_event_payload(payload: Dict[str, Any], is_update: bool = False) -> None:
    """
    Validate event create or update payload.
    
    Args:
        payload: The data dictionary to validate.
        is_update: If True, required fields are not enforced.
        
    Raises:
        ValidationError: If validation fails.
    """
    if not is_update:
        _ensure_keys(payload, ["event_date", "location", "attendees"], entity="événement")
    
    # Validate and normalize event_date
    if "event_date" in payload and payload["event_date"] is not None:
        try:
            normalize_date_in_payload(payload, "event_date")
        except DateParseError as e:
            raise ValidationError(str(e), field="event_date")
    
    # Validate location
    if "location" in payload and payload["location"] is not None:
        if not isinstance(payload["location"], str):
            raise ValidationError("Le lieu doit être une chaîne de caractères", field="location")
        if not payload["location"].strip():
            raise ValidationError("Le lieu ne peut pas être vide", field="location")
    
    # Validate attendees
    if "attendees" in payload and payload["attendees"] is not None:
        try:
            attendees = int(payload["attendees"])
            if attendees < 0:
                raise ValidationError(
                    "Le nombre de participants ne peut pas être négatif",
                    field="attendees"
                )
            payload["attendees"] = attendees  # Normalize to int
        except (TypeError, ValueError):
            raise ValidationError(
                "Le nombre de participants doit être un entier",
                field="attendees"
            )
    
    # Validate support_contact_id if provided
    if "support_contact_id" in payload and payload["support_contact_id"] is not None:
        try:
            payload["support_contact_id"] = int(payload["support_contact_id"])
        except (TypeError, ValueError):
            raise ValidationError(
                "L'ID du contact support doit être un entier",
                field="support_contact_id"
            )