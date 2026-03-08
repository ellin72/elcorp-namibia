# Elcorp Namibia

Elcorp Namibia is a multi-surface platform for identity, compliance, workflow, and operational management. The repository combines a Flask backend, server-rendered web flows, a React frontend, REST APIs, background processing, database migrations, monitoring hooks, and production deployment assets.

At a high level, the codebase supports:

- Web-based authentication and administration
- JWT-based API access for frontend and mobile-style clients
- User, profile, role, and service request management
- Dashboard and analytics endpoints for staff and admin workflows
- Audit logging, rate limiting, password reset controls, and 2FA-related safeguards
- Celery-based background jobs for email, SLA tracking, cleanup, and backups
- Docker-based local and production deployment paths

## Table of Contents

- [Project Overview](#project-overview)
- [Current Scope](#current-scope)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Repository Layout](#repository-layout)
- [Core Domain Model](#core-domain-model)
- [Security Model](#security-model)
- [Backend Surfaces](#backend-surfaces)
- [Frontend Portals](#frontend-portals)
- [API Reference Summary](#api-reference-summary)
- [Environment Configuration](#environment-configuration)
- [Local Development](#local-development)
- [Database and Migrations](#database-and-migrations)
- [Background Jobs and Reliability](#background-jobs-and-reliability)
- [Testing and Quality](#testing-and-quality)
- [Docker and Deployment](#docker-and-deployment)
- [Monitoring, Logging, and Operations](#monitoring-logging-and-operations)
- [Documentation Map](#documentation-map)
- [Troubleshooting](#troubleshooting)

## Project Overview

This repository is not a single-purpose demo. It is a combined application platform with three major delivery modes:

1. A Flask application serving HTML pages, admin tooling, and classic authenticated flows.
2. A REST API layer under `/api` for broader backend-driven features such as users, profiles, dashboards, roles, and service request workflows.
3. A JWT-oriented API layer under `/api/v1` designed for frontend and mobile-style clients, paired with a React + Vite frontend in `frontend/`.

The platform centers on user identity, operational requests, analytics, auditability, and deployment readiness.

## Current Scope

### Functional areas

- Authentication, registration, login, logout, password reset, and password history protection
- Role-based access control for admin, staff, and end-user responsibilities
- User profiles and account management
- VIN and vehicle-related data models
- Service request creation, submission, assignment, review, status changes, filtering, and history tracking
- Staff and admin dashboards, workload views, trend summaries, export, and analytics
- Asynchronous jobs for email, SLA checks, cleanup, and backups
- Monitoring and health endpoints

### Delivery surfaces

- Flask blueprints for server-rendered pages: `main`, `auth`, `dashboard`, `vin`, `admin`
- REST API blueprint at `/api`
- JWT/mobile/frontend API blueprint at `/api/v1`
- React frontend with user, staff, and admin portal entry points

## Architecture

### High-level design

```text
Clients
  |- Browser users (server-rendered Flask UI)
  |- React frontend on Vite
  |- API consumers / mobile-style clients

Application layer
  |- Flask app factory in app/__init__.py
  |- Blueprints for auth, main, dashboard, vin, admin
  |- REST APIs in app/api and app/api_v1

Persistence and state
  |- SQLAlchemy models in app/models.py
  |- Alembic migrations in migrations/
  |- SQLite for simple development, PostgreSQL for containerized and production setups

Async and operations
  |- Celery workers and beat scheduler
  |- Redis broker/result backend
  |- Backup and restore scripts
  |- Prometheus/Grafana production stack
```

### Flask application factory responsibilities

The app factory in `app/__init__.py` is responsible for:

- loading environment variables with `python-dotenv`
- validating integer configuration values early
- configuring Flask, SQLAlchemy, Alembic, LoginManager, Mail, Limiter, and CSRF
- enabling CORS for `/api/*`
- registering all web and API blueprints
- configuring application, API, and password-reset audit logging
- initializing Flask-Admin

### Backend API split

There are two API layers on purpose:

- `/api`:
  session-oriented and broader operational API surface, including admin/staff dashboards and full service request workflows.
- `/api/v1`:
  token-based API with JWT login, refresh, logout, profile access, and core service request flows intended for frontend and mobile clients.

## Technology Stack

### Backend

- Python 3.10+ compatible runtime, with current dependencies supporting modern Python versions
- Flask
- Flask-SQLAlchemy
- Flask-Migrate / Alembic
- Flask-Login
- Flask-Limiter
- Flask-Mail
- Flask-WTF
- PyJWT
- bcrypt / passlib / argon2-cffi
- Redis
- Celery
- PostgreSQL or SQLite

### Frontend

- React 18
- TypeScript
- Vite
- React Router
- Axios + axios-retry
- React Hook Form
- Zod
- Bootstrap / React-Bootstrap
- Vitest and Testing Library
- Playwright

### Quality and tooling

- Pytest
- pytest-cov
- pytest-xdist
- mypy
- ruff
- black
- bandit
- Prettier
- ESLint
- Husky / lint-staged

## Repository Layout

```text
elcorp-namibia/
|- app/                          Flask application package
|  |- api/                       Operational REST API
|  |- api_v1/                    JWT/mobile/frontend API
|  |- auth/                      Authentication web routes and forms
|  |- dashboard/                 Dashboard web routes
|  |- main/                      Main site routes
|  |- vin/                       VIN-related web routes
|  |- admin/                     Flask-Admin integration
|  |- services/                  Analytics, export, SLA services
|  |- security/                  Rate limiting and related logic
|  |- templates/                 Server-rendered HTML templates
|  |- static/                    CSS, JS, images
|  |- models.py                  Main SQLAlchemy models
|  |- celery_app.py              Celery configuration
|  |- tasks.py                   Background tasks
|  |- monitoring.py              Health/metrics integration
|  |- audit.py                   Audit helpers
|  |- email.py / email_service.py Email-related functionality
|
|- frontend/                     React + Vite frontend application
|  |- src/apps/user-portal/      User portal
|  |- src/apps/staff-portal/     Staff portal
|  |- src/apps/admin-portal/     Admin portal
|  |- src/shared/                Shared API client, auth context, types, components
|
|- migrations/                   Alembic migrations
|- tests/                        Backend test suite
|- backend/                      Additional backend/domain-oriented code and tests
|- docs/                         Topic-focused documentation
|- scripts/                      Backup and restore scripts
|- docker-compose.yml            Local container stack
|- docker-compose.production.yml Production-oriented stack
|- Dockerfile*                   Container images for different targets
|- requirements.txt              Python dependencies
|- pytest.ini                    Backend test configuration
|- alembic.ini                   Migration configuration
|- wsgi.py                       WSGI entrypoint
```

## Core Domain Model

Primary SQLAlchemy models defined in `app/models.py`:

- `Role`
- `User`
- `VinRecord`
- `AuditLog`
- `PasswordHistory`
- `PasswordResetAudit`
- `Vehicle`
- `Transaction`
- `UserProfile`
- `ServiceRequest`
- `ServiceRequestHistory`
- `DeviceToken`

These models support identity, security auditing, workflow state transitions, profile data, and token/device tracking.

## Security Model

The project includes multiple security controls across web and API layers:

- role-based access control for admin, staff, and users
- password hashing and password history enforcement
- password reset token generation and auditing
- rate limiting on sensitive routes
- CSRF protection for form-based flows
- session cookie hardening via HTTPOnly, SameSite, and secure-mode toggles
- JWT access and refresh tokens for `/api/v1`
- device-aware refresh token storage through `DeviceToken`
- audit logging for important auth and workflow events
- optional CORS configuration for trusted frontend origins only

### Roles

| Role    | Purpose                                                                               |
| ------- | ------------------------------------------------------------------------------------- |
| `admin` | system administration, elevated management, dashboards, assignment and access control |
| `staff` | operational processing, review, workload, and status management                       |
| `user`  | self-service account access and request submission                                    |

## Backend Surfaces

### Web blueprints

The Flask application registers the following web-facing blueprints:

- `main`
- `auth`
- `vin`
- `dashboard`
- `admin`

These drive the server-rendered experience under `app/templates/` and `app/static/`.

### Operational API under `/api`

This is the larger feature-rich API layer. Based on the current route inventory, it includes:

- health check endpoint
- user CRUD and role update endpoints
- profile read/update endpoints
- role listing
- current user endpoints
- service request creation, listing, filtering, assignment, submission, status changes, update, delete, and retrieval
- dashboard endpoints for admin and staff summaries, trends, workload, SLA breaches, performance, and filtered request views

### JWT/frontend/mobile API under `/api/v1`

This is the compact token-based API surface currently implemented for the React frontend and similar clients. It includes:

- login
- register
- refresh token
- logout
- logout everywhere
- token validation
- current user info
- current user profile read/update
- create service request
- list current user's service requests
- get a specific service request

## Frontend Portals

The `frontend/` application is a separate React + Vite project intended to consume the Flask backend.

### Portal entry points

- User portal: `/user`
- Staff portal: `/staff`
- Admin portal: `/admin`

### Frontend responsibilities

- authentication state management
- token-aware API client calls to `/api/v1`
- user registration and login flows
- profile views and edits
- service request creation and viewing
- shared UI primitives and types

### Frontend scripts

```bash
cd frontend
npm install
npm run dev
npm run build
npm run preview
npm run lint
npm run format
npm run type-check
npm run test
npm run test:coverage
npm run e2e
```

## API Reference Summary

### Base URLs

| Surface                 | Base URL                       |
| ----------------------- | ------------------------------ |
| Web app                 | `http://localhost:5000/`       |
| Operational API         | `http://localhost:5000/api`    |
| JWT/mobile/frontend API | `http://localhost:5000/api/v1` |
| Frontend dev server     | `http://localhost:5173`        |

### `/api` endpoint inventory

#### Health and user management

- `GET /api/health`
- `GET /api/users`
- `GET /api/users/<user_id>`
- `POST /api/users`
- `PUT /api/users/<user_id>`
- `DELETE /api/users/<user_id>`
- `PUT /api/users/<user_id>/role`
- `GET /api/profiles/<user_id>`
- `PUT /api/profiles/<user_id>`
- `GET /api/roles`
- `GET /api/me`
- `GET /api/me/profile`
- `PUT /api/me/profile`

#### Service requests

- `POST /api/service-requests`
- `GET /api/service-requests`
- `GET /api/service-requests/mine`
- `GET /api/service-requests/assigned`
- `GET /api/service-requests/<request_id>`
- `PUT /api/service-requests/<request_id>`
- `DELETE /api/service-requests/<request_id>`
- `POST /api/service-requests/<request_id>/submit`
- `PATCH /api/service-requests/<request_id>/status`
- `POST /api/service-requests/<request_id>/assign`
- `GET /api/requests/filtered`

#### Dashboard and analytics

- `GET /api/admin/summary`
- `GET /api/admin/trends`
- `GET /api/admin/workload`
- `GET /api/admin/sla-breaches`
- `GET /api/staff/summary`
- `GET /api/staff/my-workload`
- `GET /api/staff/performance`

### `/api/v1` endpoint inventory

#### Authentication

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/logout-everywhere`
- `GET /api/v1/auth/validate`

#### Current user and profile

- `GET /api/v1/me`
- `GET /api/v1/me/profile`
- `PUT /api/v1/me/profile`

#### Service requests

- `GET /api/v1/service-requests/mine`
- `POST /api/v1/service-requests`
- `GET /api/v1/service-requests/<request_id>`

### Example JWT login request

```bash
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePassword123!",
    "device_id": "device_12345"
  }'
```

### Example create service request

```bash
curl -X POST http://localhost:5000/api/v1/service-requests \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "VIN Verification",
    "description": "Need to verify a vehicle identification number",
    "category": "compliance",
    "priority": "high"
  }'
```

## Environment Configuration

### Backend `.env`

Copy `.env.example` to `.env` and review every value.

```bash
copy .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

### Important backend variables

| Variable                      | Purpose                                                                                   |
| ----------------------------- | ----------------------------------------------------------------------------------------- |
| `FLASK_ENV`                   | development or production mode                                                            |
| `FLASK_APP`                   | Flask entrypoint, currently `wsgi.py`                                                     |
| `SECRET_KEY`                  | Flask secret and current JWT signing source in `api_v1`                                   |
| `DATABASE_URL`                | SQLAlchemy database connection string                                                     |
| `MAIL_SERVER`                 | SMTP server                                                                               |
| `MAIL_PORT`                   | SMTP port                                                                                 |
| `MAIL_USE_TLS`                | enable TLS for mail                                                                       |
| `MAIL_USE_SSL`                | enable SSL for mail                                                                       |
| `MAIL_USERNAME`               | SMTP username                                                                             |
| `MAIL_PASSWORD`               | SMTP password                                                                             |
| `MAIL_DEFAULT_SENDER`         | default sender address                                                                    |
| `ADMINS`                      | comma-separated admin email list                                                          |
| `PASSWORD_RESET_TOKEN_EXPIRY` | reset token TTL in seconds                                                                |
| `PASSWORD_HISTORY_COUNT`      | number of historic passwords to reject                                                    |
| `REQUIRE_2FA_REAUTH`          | toggle for re-authentication requirements                                                 |
| `API_ITEMS_PER_PAGE`          | default pagination size                                                                   |
| `MAX_CONTENT_LENGTH`          | max request payload size                                                                  |
| `SESSION_COOKIE_HTTPONLY`     | cookie hardening                                                                          |
| `SESSION_COOKIE_SAMESITE`     | cookie cross-site policy                                                                  |
| `SESSION_COOKIE_SECURE`       | secure-cookie toggle                                                                      |
| `REDIS_URL`                   | Redis location for related services                                                       |
| `SENTRY_DSN`                  | optional Sentry DSN                                                                       |
| `PROMETHEUS_ENABLED`          | toggle for metrics exposure                                                               |
| `JWT_SECRET`                  | present in template for deployment compatibility; current `api_v1` code uses `SECRET_KEY` |
| `GIT_COMMIT_SHA`              | deployment metadata                                                                       |
| `APP_VERSION`                 | deployment metadata                                                                       |
| `BUILD_DATE`                  | deployment metadata                                                                       |
| `DOCKER_IMAGE_TAG`            | deployment metadata                                                                       |

### Frontend `.env`

The frontend uses `frontend/.env.example`.

| Variable                         | Purpose                                                        |
| -------------------------------- | -------------------------------------------------------------- |
| `VITE_API_BASE_URL`              | backend API base URL, typically `http://localhost:5000/api/v1` |
| `VITE_APP_NAME`                  | frontend display name                                          |
| `VITE_ENABLE_NOTIFICATIONS`      | client-side notification toggle                                |
| `VITE_TOKEN_EXPIRY_MINUTES`      | expected access token lifetime                                 |
| `VITE_REFRESH_TOKEN_EXPIRY_DAYS` | expected refresh token lifetime                                |

### CORS

The Flask app reads `CORS_ORIGINS` and defaults to:

- `http://localhost:5173`
- `http://localhost:3000`

Adjust this for deployed frontend origins.

## Local Development

### Prerequisites

- Python 3.10+
- Node.js 18+
- pip
- npm
- SQLite for minimal local setup, or PostgreSQL for parity with containerized environments
- Redis if you want to run Celery-backed features locally

### Backend setup

#### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
flask db upgrade
python reset_db.py
flask run
```

#### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
flask db upgrade
python reset_db.py
flask run
```

The Flask app will be available at `http://localhost:5000`.

### Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The frontend dev server will be available at `http://localhost:5173`.

### Recommended development workflow

1. Start the Flask backend.
2. Run database migrations.
3. Seed or reset local data if required.
4. Start the frontend dev server in `frontend/`.
5. Run backend and frontend tests before merging changes.

## Database and Migrations

Alembic is configured at the repository root and under `migrations/`.

### Common commands

```bash
flask db upgrade
flask db downgrade
flask db migrate -m "describe your change"
python create_migration.py
python reset_db.py
```

### Data stores in play

- SQLite for simple local development
- PostgreSQL for Docker and production-oriented deployments
- Redis for Celery broker/result backend and related operational workflows

## Background Jobs and Reliability

Celery is configured in `app/celery_app.py` and uses:

- broker URL from `CELERY_BROKER_URL`
- result backend from `CELERY_RESULT_BACKEND`
- JSON serialization
- automatic retries
- multiple named queues: `default`, `email`, `reports`, `exports`, `analytics`, `backup`, `dlq`

### Built-in periodic jobs

- SLA breach checks every 5 minutes
- old audit log cleanup daily
- nightly database backup scheduling

### Reliability features present in the codebase

- task retry configuration
- worker child recycling
- late acknowledgements
- worker-lost rejection / requeue behavior
- backup and restore scripts in `scripts/`
- SLA-related testing and monitoring hooks

## Testing and Quality

### Backend tests

The backend uses Pytest with `pytest.ini` configured to:

- add the repository root to `pythonpath`
- use `tests/` as the primary backend test path
- run with `--maxfail=1 --disable-warnings -q`

### Backend test coverage areas

Current test modules cover:

- API health and user/profile/role endpoints
- authentication flows and password reset
- audit helper presence
- RBAC and model behavior
- service request model, permissions, workflow, assignment, filtering, history, invalid transitions, and audit logging
- dashboard analytics, exports, and performance paths
- reliability concerns such as Celery tasks, SLA tracking, health checks, rate limiting, backup/recovery, monitoring, and retries

### Backend commands

```bash
pytest
pytest -v
pytest --cov=app
pytest tests/test_api.py
pytest tests/test_service_requests.py
```

### Frontend commands

```bash
cd frontend
npm run lint
npm run format
npm run type-check
npm run test
npm run test:coverage
npm run e2e
```

## Docker and Deployment

### Local Docker stack

`docker-compose.yml` provides:

- PostgreSQL 15
- Redis 7
- Flask web container

Typical use:

```bash
docker compose up --build
```

### Production-oriented stack

`docker-compose.production.yml` provides:

- PostgreSQL
- Redis with password protection
- Flask web app using `Dockerfile.production`
- Celery default worker
- Celery email worker
- Celery beat scheduler
- Prometheus
- Grafana

Typical use:

```bash
docker compose -f docker-compose.production.yml up --build -d
```

### Container assets

- `Dockerfile`
- `Dockerfile.dev`
- `Dockerfile.production`

Choose the one that matches your environment and expectations.

### Production deployment considerations

- set a real `SECRET_KEY`
- use PostgreSQL, not SQLite
- configure SMTP correctly
- configure Redis credentials and broker URLs
- set `SESSION_COOKIE_SECURE=true`
- tighten `CORS_ORIGINS` to trusted domains only
- provide persistent volumes for logs and database data
- review monitoring and backup settings before go-live

## Monitoring, Logging, and Operations

### Health endpoints

- `GET /api/health`
- `GET /health`

### Logging

The app configures log files under `app/logs/`, including:

- application-related logs
- API logs
- password reset audit logs

### Monitoring and observability

The codebase includes:

- Prometheus integration points
- Grafana in the production compose stack
- Sentry configuration placeholder via `SENTRY_DSN`
- monitoring helpers in `app/monitoring.py`

### Backup and recovery tooling

- `scripts/backup_database.sh`
- `scripts/restore_database.sh`

These scripts support compressed backups and optional encryption for backups, plus destructive restore confirmation.

## Documentation Map

For deeper detail than a single README should carry, use these documents:

- `DOCUMENTATION_INDEX.md`: central navigation for project docs
- `QUICK_START.md`: fast setup for backend and frontend
- `DEVELOPER_GUIDE.md`: day-to-day commands and development patterns
- `FRONTEND_ARCHITECTURE.md`: frontend-specific architecture details
- `docs/README.md`: docs landing page
- `docs/MOBILE_INTEGRATION.md`: mobile/API integration details
- `docs/SERVICE_REQUEST_SYSTEM.md`: service request domain details
- `docs/OPERATIONS_GUIDE.md`: operations-oriented guidance
- `DEPLOYMENT_OPERATIONS_GUIDE.md`: deployment and operational workflows
- `SECURITY.md` and `SECURITY_HARDENING_GUIDE.md`: security posture and hardening notes
- `ARCHITECTURE_PRODUCTION.md`: production architecture context

## Troubleshooting

### App fails to start

- verify `.env` exists and required variables are set
- confirm the virtual environment is active
- confirm dependencies installed successfully from `requirements.txt`
- confirm database connection string is valid

### Migrations fail

- run `flask db upgrade` again after checking `DATABASE_URL`
- inspect `migrations/versions/` for the expected migration files
- verify your database user has schema permissions

### Frontend cannot reach the backend

- confirm Flask is running on port 5000
- confirm `VITE_API_BASE_URL` points to `/api/v1`
- confirm `CORS_ORIGINS` includes the frontend origin

### JWT-authenticated requests fail

- confirm `Authorization: Bearer <token>` is sent correctly
- confirm the token is not expired
- confirm the backend `SECRET_KEY` has not changed between token issuance and validation

### Background tasks are not processing

- confirm Redis is running
- confirm Celery broker/backend variables are set
- confirm Celery workers are running for the intended queues

### Monitoring stack is not healthy

- confirm Prometheus and Grafana services are running in the production compose stack
- confirm the `/health` endpoint is reachable from the web container

## License

Proprietary - Elcorp Namibia
