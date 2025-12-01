# EPIC Events — Secure CRM Backend  
A complete Python backend for managing clients, contracts, events, and collaborators, built with:

- Python 3  
- SQLAlchemy ORM  
- Typer CLI  
- Alembic (database migrations)  
- Passlib (bcrypt hashing)  
- JSON Web Tokens (JWT authentication)  
- Sentry (logging and monitoring)

This project implements a secure architecture with role-based access control (RBAC), CRUD operations, and an interactive command-line interface.

---

#  Features

###  Security & Authentication
- JWT-based session system  
- Password hashing using **bcrypt**  
- Secure login/logout  
- Admin-only privileged actions  

###  RBAC (Role-Based Access Control)
- Roles (gestion, commercial, support…)  
- Permissions (client.read, contract.write, event.write…)  
- Automatic mapping between roles and allowed operations  

### CRUD Operations
- Manage **Users**  
- Manage **Clients**  
- Manage **Contracts**  
- Manage **Events**  
- Validation of payloads before database writes  

### Developer Tooling
- Typer CLI with:
  - Interactive menu (`python -m crm.cli run`)
  - Admin utilities
  - Data creation/update/delete
- Sentry integrated for:
  - Logging unexpected errors  
  - Tracking user/contract/event updates  

---

# Project Structure

```
crm/
 ├── auth.py                  # Authentication + JWT
 ├── cli.py                   # Command-line interface
 ├── db.py                    # DB engine and session helper
 ├── models.py                # SQLAlchemy ORM models
 ├── security.py              # Password hashing
 ├── principal.py             # Principal object after login
 ├── seeds.py                 # Admin + RBAC seeding
 ├── services/                # Business logic
 │     ├── user_service.py
 │     ├── client_service.py
 │     ├── contract_service.py
 │     └── event_service.py
 ├── ui/                      # CLI table rendering + validators
 │     ├── tables.py
 │     └── validators.py

alembic/
 ├── env.py                   # Alembic environment
 └── versions/                # Database migrations
```

---

#  Installation

```bash
git clone https://github.com/USERNAME/REPO.git
cd REPO
```

Create virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

#  Database Setup

Run Alembic migrations:

```bash
alembic upgrade head
```

---

#  RBAC Seeding

Create default roles + permissions:

```bash
python -m crm.cli rbac-seed
```

Create the main admin:

```bash
python -m crm.cli users seed-admin
```

---

#  Authentication

Login:

```bash
python -m crm.cli login
```

Logout:

```bash
python -m crm.cli logout
```

---

#  User Management

Create a collaborator:

```bash
python -m crm.cli users create user@mail.com --full-name "User Name"
```

Promote a user:

```bash
python -m crm.cli users promote user@mail.com --role-name support
```

Delete a user:

```bash
python -m crm.cli users delete --email user@mail.com
```

---

#  Client Management

Create a client:

```bash
python -m crm.cli clients create '{"full_name": "Client Test", "email": "client@mail.com"}'
```

Update a client:

```bash
python -m crm.cli clients update 1 '{"company": "NewCorp"}'
```

List clients:

```bash
python -m crm.cli clients list
```

---

#  Contract Management

Create a contract:

```bash
python -m crm.cli contracts create 1 '{"total_amount":1000,"amount_due":1000,"status":"PENDING"}'
```

Update a contract:

```bash
python -m crm.cli contracts update 1 '{"status":"SIGNED"}'
```

List contracts:

```bash
python -m crm.cli contracts list
```

---

#  Event Management

Create event:

```bash
python -m crm.cli events create 1 '{"event_date":"2025-06-01T10:00:00","location":"Paris","attendees":100}'
```

Update event:

```bash
python -m crm.cli events update 1 '{"attendees":150}'
```

List events:

```bash
python -m crm.cli events list
```

---

#  Interactive Mode

Launch the full interactive CRM:

```bash
python -m crm.cli run
```

This mode allows:
- Login  
- Create clients  
- Create contracts  
- Create events  
- List all data  
- Admin operations  

---

#  Sentry Integration

Export environment variables:

```bash
export SENTRY_DSN="https://YOUR_KEY.ingest.de.sentry.io/PROJECT_ID"
export SENTRY_ENV="development"
export SENTRY_TRACES="0.0"
```

Test Sentry:

```bash
python -c "import sentry_sdk; sentry_sdk.init(dsn='$SENTRY_DSN'); 1/0"
```

---

#  Database Schema

The schema image is available at:
 **crm_schema.png**  
 https://dbdiagram.io/d/691cc4c66735e111706ab546
 
---

#  GitHub Deployment

```bash
git add .
git commit -m "Full backend completed: CRUD + RBAC + Typer CLI + Sentry logging"
git push origin main
```

---

#  Default Credentials (example)

- **Admin**  
  Email: admin@epic.local
  Password: admin123

commercial1@epic.local
commercial2@epic.local

controler la saisir utilisitaur avant d'envoyer json
transformer la date fr en iso la ou j'exploite le json

pour l'heure d'éxiger un format iso 
au lieu de date time, date puis l'heure (pour que l'utilisateur ne se trompe pas)

gestion d'exeption 

chiffrements
chiffre les infos quand tu les mets en base 
et déchiffre pour les lire 
example sous forme de décorateurs