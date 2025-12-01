"""
Business logic services for the CRM application.

This package contains all service modules that implement
the core business logic for managing users, clients, contracts, and events.
"""

from .user_service import (
    get_user_by_email,
    create_user,
    promote_user_to_role,
    set_password,
    delete_user,
)

from .client_service import (
    create_client,
    update_client,
    get_client,
    get_clients_for_user,
)

from .contract_service import (
    create_contract,
    update_contract,
    get_contract,
    get_unsigned_contracts,
    get_unpaid_contracts,
    get_contracts_for_client,
)

from .event_service import (
    create_event,
    update_event,
    get_event,
    get_events_without_support,
    get_events_for_support,
    get_events_for_contract,
    assign_support_contact,
)

from .read_services import (
    list_clients,
    list_contracts,
    list_events,
    get_client_by_id,
    get_contract_by_id,
    get_event_by_id,
    list_clients_for_commercial,
    list_contracts_unsigned,
    list_contracts_unpaid,
    list_contracts_for_commercial,
    list_events_without_support,
    list_events_for_support,
    list_events_by_date,
)

__all__ = [
    # User service
    "get_user_by_email",
    "create_user",
    "promote_user_to_role",
    "set_password",
    "delete_user",
    # Client service
    "create_client",
    "update_client",
    "get_client",
    "get_clients_for_user",
    # Contract service
    "create_contract",
    "update_contract",
    "get_contract",
    "get_unsigned_contracts",
    "get_unpaid_contracts",
    "get_contracts_for_client",
    # Event service
    "create_event",
    "update_event",
    "get_event",
    "get_events_without_support",
    "get_events_for_support",
    "get_events_for_contract",
    "assign_support_contact",
    # Read services
    "list_clients",
    "list_contracts",
    "list_events",
    "get_client_by_id",
    "get_contract_by_id",
    "get_event_by_id",
    "list_clients_for_commercial",
    "list_contracts_unsigned",
    "list_contracts_unpaid",
    "list_contracts_for_commercial",
    "list_events_without_support",
    "list_events_for_support",
    "list_events_by_date",
]