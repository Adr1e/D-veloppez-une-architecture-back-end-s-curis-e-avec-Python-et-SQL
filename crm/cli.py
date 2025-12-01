"""
EPIC Events CRM - Command Line Interface.

This module provides the main CLI using Typer, with:
- User management commands
- Client/Contract/Event CRUD commands
- Interactive menu mode
- Proper error handling with user-friendly messages
"""

import json
import secrets
import typer

from .db import get_db
from .models import User, Role
from .services.user_service import delete_user
from .services.read_services import list_clients, list_contracts, list_events
from .services.client_service import create_client, update_client
from .services.contract_service import create_contract, update_contract
from .services.event_service import create_event, update_event
from .security import hash_password
from .seeds import seed_rbac
from .auth import (
    login_cli,
    logout,
    get_current_principal,
    ensure_admin,
)
from .principal import Principal
from .ui import (
    console,
    print_users_table,
    print_clients_table,
    print_contracts_table,
    print_events_table,
    validate_client_payload,
    validate_contract_payload,
    validate_event_payload,
    ValidationError,
    DateParseError,
)
from .exceptions import (
    CRMException,
    AuthenticationError,
    AuthorizationError,
    NotAuthenticatedError,
    OwnershipError,
    EntityNotFoundError,
    BusinessRuleError,
    format_exception_for_cli,
)

# Root Typer app for the whole CRM command line interface.
app = typer.Typer(help="EPIC Events CRM - Interface en ligne de commande")

# Sub-apps to group commands by domain.
users_app = typer.Typer(help="Gestion des collaborateurs")
clients_app = typer.Typer(help="Gestion des clients")
contracts_app = typer.Typer(help="Gestion des contrats")
events_app = typer.Typer(help="Gestion des événements")

# Register sub-apps into the main Typer application.
app.add_typer(users_app, name="users")
app.add_typer(clients_app, name="clients")
app.add_typer(contracts_app, name="contracts")
app.add_typer(events_app, name="events")


# =============================================================================
# ERROR HANDLING UTILITIES
# =============================================================================

def _handle_error(exc: Exception) -> None:
    """
    Handle an exception and display a user-friendly message.
    
    Args:
        exc: The exception to handle.
    """
    if isinstance(exc, SystemExit):
        # Typer uses SystemExit to stop a command - ignore it
        return
    
    if isinstance(exc, ValidationError):
        console.print(f"[red]Erreur de validation:[/red] {exc}")
    elif isinstance(exc, DateParseError):
        console.print(f"[red]Erreur de date:[/red] {exc}")
    elif isinstance(exc, NotAuthenticatedError):
        console.print(f"[yellow]Non connecté:[/yellow] {exc}")
    elif isinstance(exc, OwnershipError):
        console.print(f"[red]Accès refusé:[/red] {exc}")
    elif isinstance(exc, AuthorizationError):
        console.print(f"[red]Permission refusée:[/red] {exc}")
    elif isinstance(exc, AuthenticationError):
        console.print(f"[red]Erreur d'authentification:[/red] {exc}")
    elif isinstance(exc, EntityNotFoundError):
        console.print(f"[yellow]Non trouvé:[/yellow] {exc}")
    elif isinstance(exc, BusinessRuleError):
        console.print(f"[red]Règle métier:[/red] {exc}")
    elif isinstance(exc, CRMException):
        console.print(f"[red]Erreur:[/red] {exc}")
    elif isinstance(exc, PermissionError):
        console.print(f"[red]Permission refusée:[/red] {exc}")
    elif isinstance(exc, ValueError):
        console.print(f"[red]Erreur:[/red] {exc}")
    elif isinstance(exc, json.JSONDecodeError):
        console.print(f"[red]JSON invalide:[/red] {exc}")
    else:
        # Unexpected error - log to Sentry
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
        console.print(f"[red]Erreur inattendue:[/red] {type(exc).__name__}: {exc}")


def _safe_call(func, *args, **kwargs) -> bool:
    """
    Call a function and handle common errors.

    Args:
        func: The function to call.
        *args: Positional arguments.
        **kwargs: Keyword arguments.
        
    Returns:
        True if the call succeeded, False otherwise.
    """
    try:
        func(*args, **kwargs)
        return True
    except SystemExit:
        return True  # Typer exit is not an error
    except Exception as exc:
        _handle_error(exc)
        return False


def _require_logged_in() -> Principal:
    """
    Ensure there is a logged-in user (valid JWT token).
    
    Returns:
        Principal: The authenticated principal.

    Raises:
        NotAuthenticatedError: If not authenticated.
    """
    try:
        return get_current_principal()
    except AuthenticationError as exc:
        console.print(f"[yellow]Vous devez être connecté:[/yellow] {exc}")
        raise


def _parse_json_data(data: str, entity_name: str = "données") -> dict:
    """
    Parse a JSON string with error handling.
    
    Args:
        data: The JSON string to parse.
        entity_name: Name of the entity for error messages.
        
    Returns:
        Parsed dictionary.
        
    Raises:
        typer.Exit: If JSON is invalid.
    """
    try:
        return json.loads(data)
    except json.JSONDecodeError as exc:
        console.print(f"[red]JSON invalide pour {entity_name}:[/red] {exc}")
        raise typer.Exit(1)


# =============================================================================
# USERS COMMANDS
# =============================================================================

@users_app.command("create")
def users_create(
    email: str,
    full_name: str = typer.Option("", "--full-name", help="Nom complet"),
    password: str = typer.Option(None, "--password", help="Mot de passe (sera hashé)"),
    employee_number: str = typer.Option(None, "--employee-number", help="Matricule"),
):
    """Créer un compte collaborateur (admin requis)."""
    principal: Principal = get_current_principal()
    ensure_admin(principal)

    with get_db() as db:
        existing = db.query(User).filter(User.email == email).one_or_none()

        if existing:
            console.print(f"[yellow]Ce collaborateur existe déjà:[/yellow] {email}")
            raise typer.Exit(0)

        show_pw = False
        if not password:
            password = secrets.token_urlsafe(12)
            show_pw = True

        user = User(
            email=email,
            full_name=full_name or None,
            password_hash=hash_password(password),
            employee_number=employee_number or None,
        )

        db.add(user)
        db.commit()

        if show_pw:
            console.print(
                f"[green]✓ Créé:[/green] {email}\n"
                f"  Mot de passe généré: [bold]{password}[/bold]\n"
                f"  (à transmettre au collaborateur de manière sécurisée)"
            )
        else:
            console.print(f"[green]✓ Créé:[/green] {email}")


@users_app.command("seed-admin")
def users_seed_admin(
    email: str = "admin@epic.local",
    full_name: str = "Administrateur",
    password: str = typer.Option(None, "--password"),
):
    """Créer l'administrateur principal (bootstrap du système)."""
    with get_db() as db:
        role = db.query(Role).filter(Role.name == "gestion").one_or_none()
        if not role:
            role = Role(name="gestion", description="Équipe de gestion")
            db.add(role)
            db.flush()

        user = db.query(User).filter(User.email == email).one_or_none()

        if not user:
            show_pw = False
            if not password:
                password = secrets.token_urlsafe(12)
                show_pw = True

            user = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                employee_number="A-000",
                role_id=role.id,
            )
            db.add(user)
            db.commit()

            if show_pw:
                console.print(
                    f"[green]✓ Admin créé:[/green] {email}\n"
                    f"  Mot de passe: [bold]{password}[/bold]"
                )
            else:
                console.print(f"[green]✓ Admin créé:[/green] {email}")
        else:
            if user.role_id != role.id:
                user.role_id = role.id
                db.commit()
                console.print(f"[cyan]Admin mis à jour:[/cyan] {email}")
            else:
                console.print(f"[yellow]Admin existe déjà:[/yellow] {email}")


@users_app.command("promote")
def users_promote(
    email: str,
    role_name: str = typer.Option("gestion", "--role-name", "-r", help="Nom du rôle"),
):
    """Promouvoir un collaborateur à un nouveau rôle (admin requis)."""
    principal = get_current_principal()
    ensure_admin(principal)

    with get_db() as db:
        user = db.query(User).filter(User.email == email).one_or_none()
        if not user:
            console.print(f"[red]Collaborateur non trouvé:[/red] {email}")
            raise typer.Exit(code=1)

        role = db.query(Role).filter(Role.name == role_name).one_or_none()
        if not role:
            role = Role(name=role_name, description=f"Rôle {role_name}")
            db.add(role)
            db.flush()

        old_role = user.role.name if user.role else "aucun"
        user.role_id = role.id
        db.commit()
        
        console.print(
            f"[green]✓ {email} promu:[/green] {old_role} → {role_name}"
        )


@users_app.command("delete")
def users_delete(
    email: str = typer.Option(..., "--email", "-e", help="Email du collaborateur"),
):
    """Supprimer un compte collaborateur (admin requis)."""
    principal = get_current_principal()
    ensure_admin(principal)

    # Prevent self-deletion
    if principal.email == email:
        console.print("[red]Vous ne pouvez pas supprimer votre propre compte.[/red]")
        raise typer.Exit(1)

    with get_db() as db:
        ok = delete_user(db, principal=principal, email=email)

        if ok:
            console.print(f"[green]✓ Supprimé:[/green] {email}")
        else:
            console.print(f"[yellow]Collaborateur non trouvé:[/yellow] {email}")


@users_app.command("list")
def users_list():
    """Lister tous les collaborateurs (admin requis)."""
    principal = get_current_principal()
    ensure_admin(principal)

    with get_db() as db:
        users = db.query(User).order_by(User.id).all()
        if not users:
            console.print("[yellow]Aucun collaborateur trouvé.[/yellow]")
            return
        print_users_table(users)


# =============================================================================
# RBAC / AUTH COMMANDS
# =============================================================================

@app.command("rbac-seed")
def rbac_seed_cmd():
    """Initialiser les rôles et permissions par défaut."""
    with get_db() as db:
        seed_rbac(db)
        console.print("[green]✓ Rôles et permissions initialisés[/green]")


@app.command("login")
def login_cmd():
    """Se connecter à l'application."""
    login_cli()


@app.command("logout")
def logout_cmd():
    """Se déconnecter de l'application."""
    logout()
    console.print("[cyan]✓ Déconnecté[/cyan]")


@app.command("whoami")
def whoami_cmd():
    """Afficher l'utilisateur actuellement connecté."""
    try:
        principal = get_current_principal()
        console.print(f"[green]Connecté en tant que:[/green] {principal.email}")
        if principal.role:
            console.print(f"[green]Rôle:[/green] {principal.role}")
    except AuthenticationError:
        console.print("[yellow]Non connecté[/yellow]")


# =============================================================================
# CLIENTS COMMANDS
# =============================================================================

@clients_app.command("list")
def clients_list():
    """Lister tous les clients."""
    principal = get_current_principal()
    with get_db() as db:
        clients = list_clients(db, principal)
        if not clients:
            console.print("[yellow]Aucun client trouvé.[/yellow]")
            return
        print_clients_table(clients)


@clients_app.command("create")
def clients_create(data: str):
    """Créer un client (JSON: full_name, email, company, phone)."""
    principal = get_current_principal()
    
    payload = _parse_json_data(data, "client")
    
    try:
        validate_client_payload(payload)
    except ValidationError as exc:
        console.print(f"[red]Données client invalides:[/red] {exc}")
        raise typer.Exit(1)

    with get_db() as db:
        client = create_client(db, principal, data=payload)
        console.print(f"[green]✓ Client créé:[/green] ID={client.id}, {client.full_name}")


@clients_app.command("update")
def clients_update(client_id: int, data: str):
    """Modifier un client existant."""
    principal = get_current_principal()
    payload = _parse_json_data(data, "client")

    with get_db() as db:
        client = update_client(db, principal, client_id=client_id, data=payload)
        console.print(f"[green]✓ Client mis à jour:[/green] ID={client.id}")


# =============================================================================
# CONTRACTS COMMANDS
# =============================================================================

@contracts_app.command("list")
def contracts_list():
    """Lister tous les contrats."""
    principal = get_current_principal()
    with get_db() as db:
        contracts = list_contracts(db, principal)
        if not contracts:
            console.print("[yellow]Aucun contrat trouvé.[/yellow]")
            return
        print_contracts_table(contracts)


def contracts_list_filtered():
    """Lister les contrats avec filtres interactifs."""
    principal = get_current_principal()
    with get_db() as db:
        contracts = list_contracts(db, principal)
        if not contracts:
            console.print("[yellow]Aucun contrat trouvé.[/yellow]")
            return

        apply_not_signed = typer.prompt(
            "Afficher uniquement les contrats non signés? (o/N)", default="n"
        )
        apply_unpaid = typer.prompt(
            "Afficher uniquement les contrats avec solde dû? (o/N)", default="n"
        )

        filtered = []
        for ct in contracts:
            status = (ct.status or "").upper()
            amount_due = float(ct.amount_due or 0)

            if apply_not_signed.lower() in ("o", "oui", "y", "yes") and status == "SIGNED":
                continue
            if apply_unpaid.lower() in ("o", "oui", "y", "yes") and amount_due <= 0:
                continue
            filtered.append(ct)

        if not filtered:
            console.print("[yellow]Aucun contrat ne correspond aux filtres.[/yellow]")
            return

        print_contracts_table(filtered)


@contracts_app.command("create")
def contracts_create(client_id: int, data: str):
    """Créer un contrat pour un client (JSON: total_amount, amount_due, status)."""
    principal = get_current_principal()
    
    payload = _parse_json_data(data, "contrat")
    
    try:
        validate_contract_payload(payload)
    except ValidationError as exc:
        console.print(f"[red]Données contrat invalides:[/red] {exc}")
        raise typer.Exit(1)

    with get_db() as db:
        contract = create_contract(db, principal, client_id=client_id, data=payload)
        console.print(
            f"[green]✓ Contrat créé:[/green] ID={contract.id} pour client {client_id}"
        )


@contracts_app.command("update")
def contracts_update(contract_id: int, data: str):
    """Modifier un contrat existant."""
    principal = get_current_principal()
    payload = _parse_json_data(data, "contrat")

    with get_db() as db:
        contract = update_contract(db, principal, contract_id=contract_id, data=payload)
        console.print(f"[green]✓ Contrat mis à jour:[/green] ID={contract.id}")


# =============================================================================
# EVENTS COMMANDS
# =============================================================================

@events_app.command("list")
def events_list():
    """Lister tous les événements."""
    principal = get_current_principal()
    with get_db() as db:
        events = list_events(db, principal)
        if not events:
            console.print("[yellow]Aucun événement trouvé.[/yellow]")
            return
        print_events_table(events)


def events_list_without_support():
    """Lister les événements sans contact support assigné."""
    principal = get_current_principal()
    with get_db() as db:
        events = list_events(db, principal)
        if not events:
            console.print("[yellow]Aucun événement trouvé.[/yellow]")
            return

        filtered = [ev for ev in events if getattr(ev, "support_contact_id", None) is None]

        if not filtered:
            console.print("[yellow]Tous les événements ont un support assigné.[/yellow]")
            return

        print_events_table(filtered)


def events_list_assigned_to_me():
    """Lister les événements assignés à l'utilisateur courant."""
    principal = get_current_principal()
    with get_db() as db:
        events = list_events(db, principal)
        if not events:
            console.print("[yellow]Aucun événement trouvé.[/yellow]")
            return

        filtered = [ev for ev in events if getattr(ev, "support_contact_id", None) == principal.id]

        if not filtered:
            console.print("[yellow]Aucun événement ne vous est assigné.[/yellow]")
            return

        print_events_table(filtered)


@events_app.command("create")
def events_create(contract_id: int, data: str):
    """
    Créer un événement pour un contrat.
    
    JSON requis: event_date, location, attendees
    Optionnel: notes, support_contact_id
    
    Formats de date acceptés:
    - ISO: 2025-06-01T10:00:00 ou 2025-06-01
    - Français: 01/06/2025, 01/06/2025 10:00, 18 avril 2025
    """
    principal = get_current_principal()
    
    payload = _parse_json_data(data, "événement")
    
    try:
        validate_event_payload(payload)
    except (ValidationError, DateParseError) as exc:
        console.print(f"[red]Données événement invalides:[/red] {exc}")
        raise typer.Exit(1)

    with get_db() as db:
        event = create_event(db, principal, contract_id=contract_id, data=payload)
        console.print(f"[green]✓ Événement créé:[/green] ID={event.id}")


@events_app.command("update")
def events_update(event_id: int, data: str):
    """Modifier un événement existant."""
    principal = get_current_principal()
    payload = _parse_json_data(data, "événement")

    # Validate date if present
    if "event_date" in payload:
        try:
            validate_event_payload(payload, is_update=True)
        except (ValidationError, DateParseError) as exc:
            console.print(f"[red]Données invalides:[/red] {exc}")
            raise typer.Exit(1)

    with get_db() as db:
        event = update_event(db, principal, event_id=event_id, data=payload)
        console.print(f"[green]✓ Événement mis à jour:[/green] ID={event.id}")


# =============================================================================
# INTERACTIVE MENU
# =============================================================================

MENU_OPTIONS = """
[bold]Menu principal[/bold]
 1. Créer un collaborateur (admin)
 2. Se connecter
 3. Se déconnecter
 4. Lister les clients
 5. Créer un client
 6. Lister les contrats
 7. Créer un contrat
 8. Lister les événements
 9. Créer un événement
10. Promouvoir un collaborateur (admin)
11. Supprimer un collaborateur (admin)
12. Modifier un client
13. Modifier un contrat
14. Modifier un événement
15. Lister les collaborateurs (admin)
16. Info personne connecté
 0. Quitter
"""


def _prompt_yes_no(message: str, default: bool = False) -> bool:
    """Prompt for yes/no response."""
    suffix = "(O/n)" if default else "(o/N)"
    response = typer.prompt(f"{message} {suffix}", default="o" if default else "n")
    return response.lower() in ("o", "oui", "y", "yes")


@app.command("run")
def run():
    """Lancer le menu interactif du CRM."""
    console.print("[bold cyan]═══ EPIC Events CRM ═══[/bold cyan]")

    while True:
        console.print(MENU_OPTIONS)
        choice = typer.prompt("Votre choix")

        if choice == "0":
            console.print("[cyan]Au revoir![/cyan]")
            break

        elif choice == "1":
                    # Create collaborator
                    email = typer.prompt("Email du collaborateur")
                    full_name = typer.prompt("Nom complet", default="")
                    password = typer.prompt("Mot de passe", hide_input=True)

                    _safe_call(
                        users_create,
                        email=email,
                        full_name=full_name,
                        password=password,
                        employee_number=None,
                    )

        elif choice == "2":
            _safe_call(login_cmd)

        elif choice == "3":
            _safe_call(logout_cmd)

        elif choice == "4":
            _safe_call(clients_list)

        elif choice == "5":
            try:
                _require_logged_in()
            except AuthenticationError:
                continue
                
            full_name = typer.prompt("Nom complet du client")
            email = typer.prompt("Email")
            company = typer.prompt("Entreprise", default="")
            phone = typer.prompt("Téléphone", default="")
            
            payload = {
                "full_name": full_name,
                "email": email,
                "company": company or None,
                "phone": phone or None,
            }
            _safe_call(clients_create, json.dumps(payload))

        elif choice == "6":
            if _prompt_yes_no("Appliquer des filtres?"):
                _safe_call(contracts_list_filtered)
            else:
                _safe_call(contracts_list)

        elif choice == "7":
            try:
                _require_logged_in()
            except AuthenticationError:
                continue
                
            try:
                client_id = int(typer.prompt("ID du client"))
                total = float(typer.prompt("Montant total"))
                due = float(typer.prompt("Montant restant dû"))
            except ValueError as e:
                console.print(f"[red]Valeur invalide:[/red] {e}")
                continue
                
            status = typer.prompt(
                "Statut (PENDING/SIGNED/CANCELLED)", default="PENDING"
            ).upper()
            
            payload = {
                "total_amount": total,
                "amount_due": due,
                "status": status,
            }
            _safe_call(contracts_create, client_id, json.dumps(payload))

        elif choice == "8":
                    # Event listing with filters
                    apply_filter = _prompt_yes_no("Appliquer des filtres?", default=False)
                    
                    if apply_filter:
                        show_no_support = _prompt_yes_no("Afficher uniquement les événements sans support?", default=False)
                        show_mine = _prompt_yes_no("Afficher uniquement mes événements?", default=False)
                        
                        if show_no_support:
                            _safe_call(events_list_without_support)
                        elif show_mine:
                            _safe_call(events_list_assigned_to_me)
                        else:
                            _safe_call(events_list)
                    else:
                        _safe_call(events_list)

        elif choice == "9":
            try:
                _require_logged_in()
            except AuthenticationError:
                continue
                
            try:
                contract_id = int(typer.prompt("ID du contrat"))
            except ValueError:
                console.print("[red]ID de contrat invalide[/red]")
                continue
            
            console.print(
                "[dim]Formats de date acceptés: 2025-06-01, 01/06/2025, "
                "01/06/2025 14:00, 18 avril 2025[/dim]"
            )
            event_date = typer.prompt("Date de l'événement")
            location = typer.prompt("Lieu")
            
            try:
                attendees = int(typer.prompt("Nombre de participants"))
            except ValueError:
                console.print("[red]Nombre de participants invalide[/red]")
                continue
            
            notes = typer.prompt("Notes", default="")

            payload = {
                "event_date": event_date,
                "location": location,
                "attendees": attendees,
            }
            if notes.strip():
                payload["notes"] = notes

            _safe_call(events_create, contract_id, json.dumps(payload))

        elif choice == "10":
            try:
                _require_logged_in()
            except AuthenticationError:
                continue
                
            email = typer.prompt("Email du collaborateur à promouvoir")
            role_name = typer.prompt(
                "Nouveau rôle (gestion/commercial/support)", default="gestion"
            )
            _safe_call(users_promote, email=email, role_name=role_name)

        elif choice == "11":
            try:
                _require_logged_in()
            except AuthenticationError:
                continue
                
            email = typer.prompt("Email du collaborateur à supprimer")
            
            if typer.prompt(f"Confirmer la suppression de {email}? (oui/non)") == "oui":
                _safe_call(users_delete, email=email)
            else:
                console.print("[yellow]Suppression annulée.[/yellow]")

        elif choice == "12":
            try:
                _require_logged_in()
            except AuthenticationError:
                continue
                
            try:
                client_id = int(typer.prompt("ID du client à modifier"))
            except ValueError:
                console.print("[red]ID invalide[/red]")
                continue
            
            console.print("[dim]Laissez vide pour conserver la valeur actuelle[/dim]")
            
            payload = {}
            for field, prompt in [
                ("full_name", "Nouveau nom"),
                ("email", "Nouvel email"),
                ("company", "Nouvelle entreprise"),
                ("phone", "Nouveau téléphone"),
            ]:
                value = typer.prompt(prompt, default="")
                if value.strip():
                    payload[field] = value

            if not payload:
                console.print("[yellow]Aucune modification.[/yellow]")
            else:
                _safe_call(clients_update, client_id, json.dumps(payload))

        elif choice == "13":
            try:
                _require_logged_in()
            except AuthenticationError:
                continue
                
            try:
                contract_id = int(typer.prompt("ID du contrat à modifier"))
            except ValueError:
                console.print("[red]ID invalide[/red]")
                continue
            
            console.print("[dim]Laissez vide pour conserver la valeur actuelle[/dim]")
            
            payload = {}
            
            total_str = typer.prompt("Nouveau montant total", default="")
            if total_str.strip():
                try:
                    payload["total_amount"] = float(total_str)
                except ValueError:
                    console.print("[yellow]Montant total ignoré (invalide)[/yellow]")
            
            due_str = typer.prompt("Nouveau montant dû", default="")
            if due_str.strip():
                try:
                    payload["amount_due"] = float(due_str)
                except ValueError:
                    console.print("[yellow]Montant dû ignoré (invalide)[/yellow]")
            
            status = typer.prompt("Nouveau statut (PENDING/SIGNED/CANCELLED)", default="")
            if status.strip():
                payload["status"] = status.upper()

            if not payload:
                console.print("[yellow]Aucune modification.[/yellow]")
            else:
                _safe_call(contracts_update, contract_id, json.dumps(payload))

        elif choice == "14":
            try:
                _require_logged_in()
            except AuthenticationError:
                continue
                
            try:
                event_id = int(typer.prompt("ID de l'événement à modifier"))
            except ValueError:
                console.print("[red]ID invalide[/red]")
                continue
            
            console.print("[dim]Laissez vide pour conserver la valeur actuelle[/dim]")
            
            payload = {}
            
            event_date = typer.prompt("Nouvelle date", default="")
            if event_date.strip():
                payload["event_date"] = event_date
            
            location = typer.prompt("Nouveau lieu", default="")
            if location.strip():
                payload["location"] = location
            
            attendees_str = typer.prompt("Nouveau nombre de participants", default="")
            if attendees_str.strip():
                try:
                    payload["attendees"] = int(attendees_str)
                except ValueError:
                    console.print("[yellow]Nombre ignoré (invalide)[/yellow]")
            
            notes = typer.prompt("Nouvelles notes", default="")
            if notes.strip():
                payload["notes"] = notes
            
            support_email = typer.prompt("Email du nouveau support (admin)", default="")
            if support_email.strip():
                payload["support_email"] = support_email

            if not payload:
                console.print("[yellow]Aucune modification.[/yellow]")
            else:
                _safe_call(events_update, event_id, json.dumps(payload))

        elif choice == "15":
            _safe_call(users_list)

        elif choice == "16":
            _safe_call(whoami_cmd)

        else:
            console.print("[yellow]Choix invalide, réessayez.[/yellow]")


def main():
    """Entry point for: python -m crm.cli"""
    app()


if __name__ == "__main__":
    main()