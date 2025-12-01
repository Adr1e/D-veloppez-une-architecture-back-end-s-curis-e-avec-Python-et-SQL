"""
Custom exceptions for the CRM application.

This module centralizes all custom exceptions used throughout the application
to provide consistent error handling and user-friendly messages.
"""

from __future__ import annotations

from typing import Optional


# =============================================================================
# BASE EXCEPTIONS
# =============================================================================

class CRMException(Exception):
    """Base exception for all CRM-specific errors."""
    
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or "CRM_ERROR"
        super().__init__(self.message)
    
    def __str__(self) -> str:
        return self.message


# =============================================================================
# AUTHENTICATION EXCEPTIONS
# =============================================================================

class AuthenticationError(CRMException):
    """Base class for authentication-related errors."""
    
    def __init__(self, message: str):
        super().__init__(message, code="AUTH_ERROR")


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""
    
    def __init__(self):
        super().__init__("Email ou mot de passe incorrect.")


class TokenExpiredError(AuthenticationError):
    """Raised when the JWT token has expired."""
    
    def __init__(self):
        super().__init__("Votre session a expiré. Veuillez vous reconnecter.")


class TokenInvalidError(AuthenticationError):
    """Raised when the JWT token is malformed or invalid."""
    
    def __init__(self):
        super().__init__("Token invalide. Veuillez vous reconnecter.")


class NotAuthenticatedError(AuthenticationError):
    """Raised when an action requires authentication but user is not logged in."""
    
    def __init__(self):
        super().__init__("Vous devez être connecté pour effectuer cette action.")


# =============================================================================
# AUTHORIZATION EXCEPTIONS
# =============================================================================

class AuthorizationError(CRMException):
    """Base class for authorization-related errors."""
    
    def __init__(self, message: str):
        super().__init__(message, code="AUTHZ_ERROR")


class PermissionDeniedError(AuthorizationError):
    """Raised when user lacks a required permission."""
    
    # Messages clairs pour chaque permission
    PERMISSION_MESSAGES = {
        "client.read": "Vous n'avez pas le droit de consulter les clients.",
        "client.write": "Vous n'avez pas le droit de créer ou modifier des clients. Seuls les commerciaux et la gestion peuvent le faire.",
        "contract.read": "Vous n'avez pas le droit de consulter les contrats.",
        "contract.write": "Vous n'avez pas le droit de créer ou modifier des contrats. Seuls les commerciaux (pour leurs clients) et la gestion peuvent le faire.",
        "event.read": "Vous n'avez pas le droit de consulter les événements.",
        "event.write": "Les membres du support ne peuvent pas créer d'événements. Seuls les commerciaux et la gestion peuvent le faire.",
        "user.read": "Vous n'avez pas le droit de consulter les collaborateurs. Réservé à la gestion.",
        "user.write": "Vous n'avez pas le droit de créer ou modifier des collaborateurs. Réservé à la gestion.",
        "user.delete": "Vous n'avez pas le droit de supprimer des collaborateurs. Réservé à la gestion.",
    }
    
    def __init__(self, permission: str, action: Optional[str] = None):
        self.permission = permission
        self.action = action
        
        # Utiliser le message personnalisé ou un message par défaut
        if permission in self.PERMISSION_MESSAGES:
            message = self.PERMISSION_MESSAGES[permission]
        elif action:
            message = f"Permission refusée pour {action}."
        else:
            message = f"Vous n'avez pas la permission requise ({permission})."
        
        super().__init__(message)


class AdminRequiredError(AuthorizationError):
    """Raised when an action requires admin (gestion) role."""
    
    def __init__(self, action: str = "cette action"):
        super().__init__(
            f"Droits administrateur requis pour {action}. "
            f"Seul le rôle 'gestion' peut effectuer cette opération."
        )


class OwnershipError(AuthorizationError):
    """Base class for ownership-related permission errors."""
    pass


class ClientOwnershipError(OwnershipError):
    """Raised when a user tries to modify a client they don't own."""
    
    def __init__(self, client_id: int):
        self.client_id = client_id
        super().__init__(
            f"Vous n'êtes pas le commercial responsable du client {client_id}. "
            f"Seul le commercial assigné peut modifier ce client."
        )


class ContractOwnershipError(OwnershipError):
    """Raised when a user tries to modify a contract they don't own."""
    
    def __init__(self, contract_id: int):
        self.contract_id = contract_id
        super().__init__(
            f"Vous n'êtes pas le commercial responsable du contrat {contract_id}. "
            f"Seul le commercial du client associé peut modifier ce contrat."
        )


class EventOwnershipError(OwnershipError):
    """Raised when a user tries to modify an event they don't own."""
    
    def __init__(self, event_id: int, role: str = ""):
        self.event_id = event_id
        self.role = role
        
        if role == "support":
            message = (
                f"Vous n'êtes pas le contact support de l'événement {event_id}. "
                f"Seul le support assigné peut modifier cet événement."
            )
        elif role == "commercial":
            message = (
                f"Les commerciaux ne peuvent pas modifier les événements. "
                f"Seuls le support assigné et la gestion peuvent le faire."
            )
        else:
            message = f"Vous n'avez pas les droits pour modifier l'événement {event_id}."
        
        super().__init__(message)


# =============================================================================
# VALIDATION EXCEPTIONS
# =============================================================================

class ValidationError(CRMException):
    """Base class for validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        code = f"VALIDATION_ERROR:{field}" if field else "VALIDATION_ERROR"
        super().__init__(message, code=code)
    
    def __str__(self) -> str:
        if self.field:
            return f"[{self.field}] {self.message}"
        return self.message


class MissingFieldError(ValidationError):
    """Raised when a required field is missing."""
    
    def __init__(self, field: str, entity: str = ""):
        self.entity = entity
        message = f"Le champ '{field}' est requis"
        if entity:
            message += f" pour {entity}"
        super().__init__(message, field=field)


class InvalidEmailError(ValidationError):
    """Raised when an email address is invalid."""
    
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Format d'email invalide: {email}", field="email")


class InvalidPhoneError(ValidationError):
    """Raised when a phone number is invalid."""
    
    def __init__(self, phone: str, field_name: str = "phone"):
        self.phone = phone
        super().__init__(f"Format de téléphone invalide: {phone}", field=field_name)


class InvalidAmountError(ValidationError):
    """Raised when a monetary amount is invalid."""
    
    def __init__(self, field: str, reason: str = "doit être un nombre positif"):
        super().__init__(f"{field} {reason}", field=field)


class InvalidStatusError(ValidationError):
    """Raised when a status value is invalid."""
    
    def __init__(self, status: str, valid_values: list[str]):
        self.status = status
        self.valid_values = valid_values
        super().__init__(
            f"Statut invalide: {status}. Valeurs acceptées: {', '.join(valid_values)}",
            field="status"
        )


class DateParseError(ValidationError):
    """Raised when a date cannot be parsed."""
    
    def __init__(self, value: str, expected_formats: Optional[list[str]] = None):
        self.value = value
        self.expected_formats = expected_formats or ["YYYY-MM-DD", "DD/MM/YYYY"]
        super().__init__(
            f"Format de date invalide: '{value}'. "
            f"Formats acceptés: {', '.join(self.expected_formats)}",
            field="date"
        )


# =============================================================================
# ENTITY EXCEPTIONS
# =============================================================================

class EntityNotFoundError(CRMException):
    """Raised when an entity is not found in the database."""
    
    def __init__(self, entity_type: str, identifier: any):
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(
            f"{entity_type} non trouvé: {identifier}",
            code=f"NOT_FOUND:{entity_type.upper()}"
        )


class UserNotFoundError(EntityNotFoundError):
    """Raised when a user is not found."""
    
    def __init__(self, identifier: any):
        super().__init__("Collaborateur", identifier)


class ClientNotFoundError(EntityNotFoundError):
    """Raised when a client is not found."""
    
    def __init__(self, client_id: int):
        super().__init__("Client", client_id)


class ContractNotFoundError(EntityNotFoundError):
    """Raised when a contract is not found."""
    
    def __init__(self, contract_id: int):
        super().__init__("Contrat", contract_id)


class EventNotFoundError(EntityNotFoundError):
    """Raised when an event is not found."""
    
    def __init__(self, event_id: int):
        super().__init__("Événement", event_id)


class RoleNotFoundError(EntityNotFoundError):
    """Raised when a role is not found."""
    
    def __init__(self, role_name: str):
        super().__init__("Rôle", role_name)


# =============================================================================
# BUSINESS RULE EXCEPTIONS
# =============================================================================

class BusinessRuleError(CRMException):
    """Base class for business rule violations."""
    
    def __init__(self, message: str):
        super().__init__(message, code="BUSINESS_RULE_ERROR")


class ContractNotSignedError(BusinessRuleError):
    """Raised when an action requires a signed contract."""
    
    def __init__(self, contract_id: int):
        self.contract_id = contract_id
        super().__init__(
            f"Le contrat {contract_id} n'est pas signé. "
            f"Cette action n'est possible que pour les contrats signés."
        )


class DuplicateEmailError(BusinessRuleError):
    """Raised when trying to create an entity with a duplicate email."""
    
    def __init__(self, email: str, entity_type: str = "utilisateur"):
        self.email = email
        self.entity_type = entity_type
        super().__init__(
            f"Un {entity_type} avec l'email '{email}' existe déjà."
        )


class SelfDeletionError(BusinessRuleError):
    """Raised when a user tries to delete themselves."""
    
    def __init__(self):
        super().__init__("Vous ne pouvez pas supprimer votre propre compte.")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_exception_for_cli(exc: Exception) -> str:
    """
    Format an exception for display in the CLI.
    
    Args:
        exc: The exception to format.
        
    Returns:
        A user-friendly error message string.
    """
    if isinstance(exc, CRMException):
        return f"[{exc.code}] {exc.message}"
    elif isinstance(exc, PermissionError):
        return f"[PERMISSION] {str(exc)}"
    elif isinstance(exc, ValueError):
        return f"[ERREUR] {str(exc)}"
    else:
        return f"[ERREUR INATTENDUE] {type(exc).__name__}: {str(exc)}"


def is_retriable_error(exc: Exception) -> bool:
    """
    Check if an error is retriable (e.g., network issues).
    
    Args:
        exc: The exception to check.
        
    Returns:
        True if the operation can be retried.
    """
    # Most CRM exceptions are not retriable
    if isinstance(exc, CRMException):
        return False
    
    # Database connection issues might be retriable
    if "connection" in str(exc).lower():
        return True
    
    return False