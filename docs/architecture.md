# Architecture

## System Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Client /   │────▶│   Flask API  │────▶│  PostgreSQL   │
│   SDK / App  │◀────│   (Gunicorn) │◀────│              │
└──────────────┘     └──────┬───────┘     └──────────────┘
                            │
                     ┌──────▼───────┐     ┌──────────────┐
                     │    Redis     │────▶│ Celery Worker │
                     │   (broker)   │◀────│              │
                     └──────────────┘     └──────────────┘
```

## Components

| Component      | Tech                 | Purpose                                |
| -------------- | -------------------- | -------------------------------------- |
| API Server     | Flask 3.1 + Gunicorn | REST API, JWT auth, RBAC               |
| Database       | PostgreSQL 15        | Users, KYC, payments, merchants, audit |
| Cache / Broker | Redis 7              | Celery task broker, rate-limit backend |
| Worker         | Celery               | Background KYC verification, email     |
| Monitoring     | Prometheus + Grafana | Metrics, dashboards, alerts            |

## Project Layout

```
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py            # Config classes
│   ├── extensions.py        # Shared extensions
│   ├── celery_app.py        # Celery factory
│   ├── models/              # SQLAlchemy models
│   ├── api/v1/              # Blueprint routes
│   ├── services/            # Business logic
│   ├── middleware/           # JWT, RBAC
│   ├── utils/               # Encryption, validation, errors
│   └── workers/             # Celery tasks
├── migrations/              # Alembic
├── tests/                   # pytest suite
├── sdks/                    # Python & Node SDKs
├── sample-app/              # Demo CLI
├── postman/                 # Postman collection
├── docs/                    # Documentation
├── k8s/                     # Kubernetes manifests
├── monitoring/              # Prometheus & Grafana configs
├── .github/workflows/       # CI/CD
├── docker-compose.yml       # Local dev stack
├── Dockerfile               # API container
└── requirements.txt         # Python deps
```

## Design Patterns

### App Factory

`create_app(config_name)` in `app/__init__.py` builds the Flask app, registers extensions, blueprints, and error handlers. Config is selected via the `FLASK_ENV` environment variable.

### Service Layer

Business logic lives in `app/services/`, not in route handlers. Routes are thin: parse input → call service → return JSON.

### Repository / ORM

SQLAlchemy models with UUID primary keys. All queries go through the ORM — no raw SQL.

### Middleware Stack

```
Request → Flask-Limiter → @jwt_required → @roles_required → Route → Service → DB
```

### Background Processing

Celery workers consume tasks from Redis. Task queues:

- `default` — general tasks
- `verification` — KYC verification checks
- `email` — notification emails

A Celery Beat schedule runs `check_pending_verifications` every 5 minutes.

## Data Model

```
User ──┬── KYCDocument (1:N)
       ├── Payment (1:N as payer)
       ├── PaymentToken (1:N)
       ├── Merchant (1:N as onboarder)
       └── AuditLog (1:N)

Merchant ── Payment (1:N as receiver)
```

## Environments

| Name        | Database        | Debug | Rate Limits |
| ----------- | --------------- | ----- | ----------- |
| development | SQLite          | on    | lenient     |
| testing     | SQLite (memory) | off   | disabled    |
| production  | PostgreSQL      | off   | strict      |
