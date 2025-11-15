import json
import secrets
import typer
from sqlalchemy.orm import Session

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
    AuthError,
)
from .principal import Principal
from .ui import (
    console,
    print_clients_table,
    print_contracts_table,
    print_events_table,
    validate_client_payload,
    validate_contract_payload,
    validate_event_payload,
)

# Root Typer app for the whole CRM command line interface.
app = typer.Typer(help="EPIC CRM CLI")

# Sub-apps to group commands by domain (users, clients, contracts, events).
users_app = typer.Typer(help="Users commands")
clients_app = typer.Typer(help="Clients commands")
contracts_app = typer.Typer(help="Contracts commands")
events_app = typer.Typer(help="Events commands")


def _safe_call(func, *args, **kwargs) -> None:
    """Call a Typer command but ignore SystemExit so the interactive menu keeps running."""
    try:
        func(*args, **kwargs)
    except SystemExit:
        # Typer uses Exit to stop a command. Here we catch it so we go back to the menu.
        pass


def _require_logged_in() -> Principal:
    """
    Ensure there is a logged-in user (valid JWT token).

    If not authenticated, it prints a message and raises the AuthError again.
    The caller can then decide to skip the action and stay in the menu.
    """
    try:
        return get_current_principal()
    except AuthError as exc:
        console.print(f"[red]You must be logged in:[/red] {exc}")
        raise


@users_app.command("create")
def users_create(
    email: str,
    full_name: str = typer.Option("", "--full-name"),
    password: str = typer.Option(
        None, "--password", help="Plain password (will be hashed)"
    ),
    employee_number: str = typer.Option(None, "--employee-number"),
):
    """
    Create a collaborator account.

    Only a user with the 'gestion' role is allowed to do this.
    If no password is provided, a random secure password is generated.
    """
    # Get the current authenticated user (from JWT token).
    principal: Principal = get_current_principal()
    # Check that this user is an administrator.
    ensure_admin(principal)

    with get_db() as db:
        # Check if a user with this email already exists.
        existing = db.query(User).filter(User.email == email).one_or_none()

        if existing:
            console.print(f"[yellow]Already exists:[/yellow] {email}")
            # Exit the command cleanly but do not kill the whole app.
            raise typer.Exit(0)

        show_pw = False
        if not password:
            # Generate a secure random password if none is provided.
            password = secrets.token_urlsafe(12)
            show_pw = True

        # Create the User object with a hashed password.
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
                f"[green]Created:[/green] {email} (generated password: {password})"
            )
        else:
            console.print(f"[green]Created:[/green] {email}")


@users_app.command("seed-admin")
def users_seed_admin(
    email: str = "admin@epic.local",
    full_name: str = "Admin",
    password: str = typer.Option(None, "--password"),
):
    """
    Create or ensure the main admin user exists.

    This command is used to bootstrap the system and does not require login.
    It also ensures the 'gestion' role exists and is assigned to this user.
    """
    with get_db() as db:
        # Ensure the 'gestion' role exists.
        role = db.query(Role).filter(Role.name == "gestion").one_or_none()
        if not role:
            role = Role(name="gestion", description="Administrator")
            db.add(role)
            db.flush()

        # Look for an existing user with this admin email.
        user = db.query(User).filter(User.email == email).one_or_none()

        if not user:
            show_pw = False
            if not password:
                # Generate a password if not provided.
                password = secrets.token_urlsafe(12)
                show_pw = True

            # Create the admin user linked to the 'gestion' role.
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
                    f"[green]Admin created:[/green] {email} (password: {password})"
                )
            else:
                console.print(f"[green]Admin created:[/green] {email}")
        else:
            # If the admin exists, just ensure they have the correct role.
            if user.role_id != role.id:
                user.role_id = role.id
                db.commit()
                console.print(f"[cyan]Admin updated:[/cyan] {email}")
            else:
                console.print(f"[yellow]Admin already exists:[/yellow] {email}")


@users_app.command("promote")
def users_promote(email: str, role_name: str = "gestion"):
    """
    Promote a collaborator by changing their role.

    Only an admin can run this command.
    If the role does not exist, it is created on the fly.
    """
    principal = get_current_principal()
    ensure_admin(principal)

    with get_db() as db:
        # Find the user to promote.
        user = db.query(User).filter(User.email == email).one_or_none()
        if not user:
            console.print(f"[red]User not found:[/red] {email}")
            raise typer.Exit(code=1)

        # Find or create the target role.
        role = db.query(Role).filter(Role.name == role_name).one_or_none()
        if not role:
            role = Role(name=role_name, description=f"Role {role_name}")
            db.add(role)
            db.flush()

        # Assign the new role to the user.
        user.role_id = role.id
        db.commit()
        console.print(f"[green]{email} promoted to {role_name}[/green]")


@users_app.command("delete")
def users_delete(
    email: str = typer.Option(..., "--email", help="Email to delete"),
):
    """
    Delete a collaborator account.

    Only an admin can delete users.
    The delete logic and checks are implemented in the service layer.
    """
    principal = get_current_principal()
    ensure_admin(principal)

    with get_db() as db:
        ok = delete_user(db, principal=principal, email=email)

        if ok:
            console.print(f"[green]Deleted {email}[/green]")
        else:
            console.print(f"[yellow]User not found:[/yellow] {email}")


@app.command("rbac-seed")
def rbac_seed_cmd():
    """
    Initialize default roles and permissions (RBAC).

    This uses the seed_rbac() helper to populate the database
    with base roles, permissions and associations.
    """
    with get_db() as db:
        seed_rbac(db)
        console.print("[green]RBAC seed: OK[/green]")


@app.command("login")
def login_cmd():
    """
    Authenticate a user and store a JWT token locally.

    The actual interactive login flow is implemented in login_cli().
    """
    login_cli()


@app.command("logout")
def logout_cmd():
    """
    Logout by removing the stored JWT token from disk.
    """
    logout()
    console.print("[cyan]Logged out[/cyan]")


@clients_app.command("list")
def clients_list():
    """
    List all clients visible for the current authenticated user.

    The service layer applies the access control rules based on the user role.
    """
    principal = get_current_principal()
    with get_db() as db:
        clients = list_clients(db, principal)
        if not clients:
            console.print("[yellow]No clients found.[/yellow]")
            return
        print_clients_table(clients)


@contracts_app.command("list")
def contracts_list():
    """
    List all contracts visible for the current authenticated user.
    """
    principal = get_current_principal()
    with get_db() as db:
        contracts = list_contracts(db, principal)
        if not contracts:
            console.print("[yellow]No contracts found.[/yellow]")
            return
        print_contracts_table(contracts)


@events_app.command("list")
def events_list():
    """
    List all events visible for the current authenticated user.
    """
    principal = get_current_principal()
    with get_db() as db:
        events = list_events(db, principal)
        if not events:
            console.print("[yellow]No events found.[/yellow]")
            return
        print_events_table(events)


@clients_app.command("create")
def clients_create(data: str):
    """
    Create a client from a JSON string passed on the command line.

    Example:
      python -m crm.cli clients create '{"full_name": "...", "email": "..."}'
    """
    principal = get_current_principal()
    try:
        payload = json.loads(data)
        validate_client_payload(payload)
    except Exception as exc:
        console.print(f"[red]Invalid client data:[/red] {exc}")
        raise typer.Exit(1)

    with get_db() as db:
        client = create_client(db, principal, data=payload)
        console.print(f"[green]Created client {client.id}[/green]")


@clients_app.command("update")
def clients_update(client_id: int, data: str):
    """
    Update an existing client using a JSON payload.

    Only fields provided in the JSON will be updated.
    """
    principal = get_current_principal()
    try:
        payload = json.loads(data)
    except Exception as exc:
        console.print(f"[red]Invalid data:[/red] {exc}")
        raise typer.Exit(1)

    with get_db() as db:
        client = update_client(db, principal, client_id=client_id, data=payload)
        console.print(f"[green]Updated client {client.id}[/green]")


@contracts_app.command("create")
def contracts_create(client_id: int, data: str):
    """
    Create a contract for a given client.

    The JSON payload should contain fields like total_amount, amount_due and status.
    """
    principal = get_current_principal()
    try:
        payload = json.loads(data)
        validate_contract_payload(payload)
    except Exception as exc:
        console.print(f"[red]Invalid contract data:[/red] {exc}")
        raise typer.Exit(1)

    with get_db() as db:
        contract = create_contract(db, principal, client_id=client_id, data=payload)
        console.print(
            f"[green]Created contract {contract.id} for client {client_id}[/green]"
        )


@contracts_app.command("update")
def contracts_update(contract_id: int, data: str):
    """
    Update an existing contract.

    Typical fields to update are amount_due and status.
    """
    principal = get_current_principal()
    try:
        payload = json.loads(data)
    except Exception as exc:
        console.print(f"[red]Invalid data:[/red] {exc}")
        raise typer.Exit(1)

    with get_db() as db:
        contract = update_contract(db, principal, contract_id=contract_id, data=payload)
        console.print(f"[green]Updated contract {contract.id}[/green]")


@events_app.command("create")
def events_create(contract_id: int, data: str):
    """
    Create a new event linked to a contract.

    The JSON payload must at least contain event_date, location and attendees.
    """
    principal = get_current_principal()
    try:
        payload = json.loads(data)
        validate_event_payload(payload)
    except Exception as exc:
        console.print(f"[red]Invalid event data:[/red] {exc}")
        raise typer.Exit(1)

    with get_db() as db:
        event = create_event(db, principal, contract_id=contract_id, data=payload)
        console.print(f"[green]Created event {event.id}[/green]")


@events_app.command("update")
def events_update(event_id: int, data: str):
    """
    Update an existing event.

    For example, you can change the location or number of attendees.
    """
    principal = get_current_principal()
    try:
        payload = json.loads(data)
    except Exception as exc:
        console.print(f"[red]Invalid data:[/red] {exc}")
        raise typer.Exit(1)

    with get_db() as db:
        event = update_event(db, principal, event_id=event_id, data=payload)
        console.print(f"[green]Updated event {event.id}[/green]")


@app.command("run")
def run():
    """
    Start the interactive CRM menu.

    This provides a simple text menu so users do not need
    to remember all Typer commands.
    """
    console.print("[bold cyan]EPIC CRM - Interactive CLI[/bold cyan]")

    while True:
        console.print("\n[bold]Main menu[/bold]")
        console.print("1. Create collaborator (admin only)")
        console.print("2. Login")
        console.print("3. Logout")
        console.print("4. List clients")
        console.print("5. Create client")
        console.print("6. List contracts")
        console.print("7. Create contract")
        console.print("8. List events")
        console.print("9. Create event")
        console.print("0. Quit")

        choice = typer.prompt("Your choice")

        if choice == "0":
            # Exit the interactive loop and terminate the CLI.
            break

        elif choice == "1":
            # Interactive collaborator creation (admin only).
            email = typer.prompt("Collaborator email")
            full_name = typer.prompt("Full name", default="")
            pwd_choice = typer.prompt("Provide password? (y/N)", default="n")
            password = None
            if pwd_choice.lower() == "y":
                password = typer.prompt("Password", hide_input=True)

            # We explicitly pass employee_number=None to avoid passing a Typer OptionInfo object.
            _safe_call(
                users_create,
                email=email,
                full_name=full_name,
                password=password,
                employee_number=None,
            )

        elif choice == "2":
            # Run the login flow (ask for email and password).
            _safe_call(login_cmd)

        elif choice == "3":
            # Logout and remove the stored token.
            _safe_call(logout_cmd)

        elif choice == "4":
            # List clients for the current user.
            _safe_call(clients_list)

        elif choice == "5":
            # Interactive client creation.
            try:
                _require_logged_in()
            except AuthError:
                # If not logged in, go back to menu.
                continue
            full_name = typer.prompt("Client full name")
            email = typer.prompt("Client email")
            company = typer.prompt("Company", default="")
            phone = typer.prompt("Phone", default="")
            mobile = typer.prompt("Mobile", default="")
            payload = {
                "full_name": full_name,
                "email": email,
                "company": company or None,
                "phone": phone or None,
                "mobile": mobile or None,
            }
            _safe_call(clients_create, json.dumps(payload))

        elif choice == "6":
            # List all contracts visible to the current user.
            _safe_call(contracts_list)

        elif choice == "7":
            # Interactive contract creation.
            try:
                _require_logged_in()
            except AuthError:
                continue
            client_id = int(typer.prompt("Client ID"))
            total = float(typer.prompt("Total amount"))
            due = float(typer.prompt("Amount due"))
            status = typer.prompt(
                "Status (PENDING/SIGNED/CANCELLED)", default="PENDING"
            )
            payload = {
                "total_amount": total,
                "amount_due": due,
                "status": status,
            }
            _safe_call(contracts_create, client_id, json.dumps(payload))

        elif choice == "8":
            # List events visible to the current user.
            _safe_call(events_list)

        elif choice == "9":
            # Interactive event creation.
            try:
                _require_logged_in()
            except AuthError:
                continue
            contract_id = int(typer.prompt("Contract ID"))
            event_date = typer.prompt("Event date (ISO: 2025-06-01T10:00:00)")
            location = typer.prompt("Location")
            attendees = int(typer.prompt("Attendees"))
            payload = {
                "event_date": event_date,
                "location": location,
                "attendees": attendees,
            }
            _safe_call(events_create, contract_id, json.dumps(payload))

        else:
            # Invalid choice: show a warning and redisplay the menu.
            console.print("[yellow]Invalid choice, try again.[/yellow]")


def main():
    """
    Entry point used when running: python -m crm.cli

    This simply delegates to the Typer app.
    """
    app()


if __name__ == "__main__":
    main()
