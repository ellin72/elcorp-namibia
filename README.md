# Elcorp Namibia — Digital Identity & Payments Platform

Production-grade platform for digital identity verification and payment processing in Namibia. Combines a full REST API backend with a web-based UI, background workers, monitoring, and deployment infrastructure.

---

## What's Included

| Module                   | Delivered                                                                                             |
| ------------------------ | ----------------------------------------------------------------------------------------------------- |
| **Identity & KYC**       | Signup, profile management, KYC document upload, automated + manual verification, audit trail         |
| **Payments Sandbox**     | Tokenised instruments, payment creation & processing, merchant onboarding, simulated payouts          |
| **Merchant Dashboard**   | API-key login, transaction overview, webhook management                                               |
| **Admin Panel**          | System stats, user management, role assignment, audit log viewer                                      |
| **Web UI**               | 11-page SPA-style frontend (landing, auth, dashboard, profile, KYC, payments, merchants, admin)       |
| **RBAC**                 | Three roles (admin, staff, user) with 13 granular permissions, enforced on every endpoint             |
| **Security**             | JWT access + refresh tokens (with rotation), bcrypt passwords, Fernet field encryption, rate limiting |
| **Background Workers**   | Celery tasks for KYC auto-verification, email dispatch, scheduled checks                              |
| **Developer Experience** | REST API, Python SDK, Node.js SDK, Postman collection, CLI commands                                   |
| **CI/CD**                | GitHub Actions — lint → test → Docker build → K8s deploy                                              |
| **Monitoring**           | Prometheus custom metrics, Grafana dashboards, structured logging (structlog)                         |
| **Infrastructure**       | Docker Compose (dev + production), Kubernetes manifests, Ingress with TLS                             |

---

## Quick Start

### Prerequisites

- Python 3.11+
- (Optional) Docker & Docker Compose
- (Optional) Redis — for Celery workers and rate limiting in production

### Local Development (SQLite)

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
cp .env.example .env              # then edit .env with your secrets
flask db upgrade
flask run
```

The first user to sign up is automatically promoted to **admin**.

### Docker Compose

```bash
docker compose up --build
```

### Production (Docker)

```bash
docker compose -f docker-compose.production.yml up --build -d
```

**Base URLs:**

| Service  | URL                             |
| -------- | ------------------------------- |
| Web UI   | `http://localhost:5000/ui/`     |
| REST API | `http://localhost:5000/api/v1/` |
| Metrics  | `http://localhost:5000/metrics` |

---

## First API Calls

```bash
# Health check
curl http://localhost:5000/api/v1/health

# Sign up (first user gets admin role automatically)
curl -X POST http://localhost:5000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@elcorp.na","password":"Demo1234!","first_name":"Demo","last_name":"User"}'

# Login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@elcorp.na","password":"Demo1234!"}'

# Authenticated request (use the access_token from login response)
curl http://localhost:5000/api/v1/me \
  -H "Authorization: Bearer <access_token>"
```

---

## API Reference

### Authentication

| Method | Endpoint                | Description               | Auth    |
| ------ | ----------------------- | ------------------------- | ------- |
| POST   | `/api/v1/auth/signup`   | Register a new user       | Public  |
| POST   | `/api/v1/auth/login`    | Authenticate & get tokens | Public  |
| POST   | `/api/v1/auth/refresh`  | Rotate refresh token      | Refresh |
| GET    | `/api/v1/auth/validate` | Validate current JWT      | Bearer  |
| POST   | `/api/v1/auth/logout`   | Revoke refresh token      | Bearer  |

### Identity & KYC

| Method | Endpoint                  | Description                  | Auth        |
| ------ | ------------------------- | ---------------------------- | ----------- |
| GET    | `/api/v1/me`              | Current user profile         | Bearer      |
| PUT    | `/api/v1/me`              | Update profile               | Bearer      |
| GET    | `/api/v1/me/permissions`  | List effective permissions   | Bearer      |
| GET    | `/api/v1/users`           | List all users (paginated)   | Admin/Staff |
| GET    | `/api/v1/users/<id>`      | Get user by ID               | Admin/Staff |
| POST   | `/api/v1/kyc/upload`      | Upload KYC document          | Bearer      |
| GET    | `/api/v1/kyc/documents`   | List own KYC documents       | Bearer      |
| POST   | `/api/v1/kyc/<id>/review` | Approve / reject KYC         | Admin/Staff |
| GET    | `/api/v1/kyc/pending`     | List pending KYC submissions | Admin/Staff |

### Payments

| Method | Endpoint                           | Description                   | Auth   |
| ------ | ---------------------------------- | ----------------------------- | ------ |
| POST   | `/api/v1/payments/tokens`          | Create tokenised instrument   | Bearer |
| POST   | `/api/v1/payments`                 | Create a payment              | Bearer |
| POST   | `/api/v1/payments/<id>/process`    | Process a payment             | Bearer |
| GET    | `/api/v1/payments/<id>`            | Get payment details           | Bearer |
| GET    | `/api/v1/payments`                 | List own payments (paginated) | Bearer |
| POST   | `/api/v1/payments/simulate-payout` | Sandbox settlement test       | Bearer |

### Merchants

| Method | Endpoint                            | Description          | Auth        |
| ------ | ----------------------------------- | -------------------- | ----------- |
| POST   | `/api/v1/merchants`                 | Onboard merchant     | Admin       |
| GET    | `/api/v1/merchants`                 | List merchants       | Admin/Staff |
| GET    | `/api/v1/merchants/<id>`            | Get merchant details | Admin/Staff |
| PUT    | `/api/v1/merchants/<id>`            | Update merchant      | Admin       |
| POST   | `/api/v1/merchants/<id>/deactivate` | Deactivate merchant  | Admin       |

### Webhooks

| Method | Endpoint                             | Description            | Auth        |
| ------ | ------------------------------------ | ---------------------- | ----------- |
| POST   | `/api/v1/webhooks`                   | Create subscription    | Admin       |
| GET    | `/api/v1/webhooks/<merchant_id>`     | List merchant webhooks | Admin/Staff |
| DELETE | `/api/v1/webhooks/<subscription_id>` | Delete subscription    | Admin       |

### Admin

| Method | Endpoint                              | Description             | Auth  |
| ------ | ------------------------------------- | ----------------------- | ----- |
| GET    | `/api/v1/admin/stats`                 | System statistics       | Admin |
| GET    | `/api/v1/admin/audit-logs`            | Paginated audit logs    | Admin |
| PUT    | `/api/v1/admin/users/<id>/roles`      | Update user roles       | Admin |
| POST   | `/api/v1/admin/users/<id>/deactivate` | Deactivate user account | Admin |

### Health

| Method | Endpoint               | Description                                  | Auth   |
| ------ | ---------------------- | -------------------------------------------- | ------ |
| GET    | `/api/v1/health`       | Basic health check                           | Public |
| GET    | `/api/v1/health/ready` | Deep check (DB, Redis, Celery, file storage) | Public |

---

## Web UI

The platform ships with a full browser-based UI served at `/ui/`. All pages fetch data from the REST API client-side using the vanilla JS client in `app/ui/static/js/api.js`.

| Page      | Route           | Description                                  |
| --------- | --------------- | -------------------------------------------- |
| Landing   | `/ui/`          | Public landing page                          |
| Login     | `/ui/login`     | Email + password authentication              |
| Sign Up   | `/ui/signup`    | New user registration                        |
| Dashboard | `/ui/dashboard` | Overview with stats and recent activity      |
| Profile   | `/ui/profile`   | View and edit user profile                   |
| KYC       | `/ui/kyc`       | Upload and track identity documents          |
| Payments  | `/ui/payments`  | Create payments and view transaction history |
| Merchants | `/ui/merchants` | Merchant onboarding and management (admin)   |
| Webhooks  | `/ui/webhooks`  | Webhook subscription management (admin)      |
| Admin     | `/ui/admin`     | System stats, audit logs, user management    |
| Health    | `/ui/health`    | Live system health status                    |

---

## Database Models

| Model                   | Purpose                                                   |
| ----------------------- | --------------------------------------------------------- |
| **User**                | Accounts with email, hashed password, verification status |
| **Role**                | Named roles (admin, staff, user)                          |
| **Permission**          | Granular permissions (e.g. `payments.create`)             |
| **KYCDocument**         | Uploaded identity documents with review workflow          |
| **Payment**             | Payment records with status lifecycle                     |
| **PaymentToken**        | Tokenised payment instruments (card, bank account)        |
| **Merchant**            | Onboarded businesses with API keys                        |
| **AuditLog**            | Immutable event log for compliance                        |
| **WebhookSubscription** | Merchant webhook endpoints and event filters              |
| **WebhookDelivery**     | Delivery attempts and results per webhook event           |
| **RevokedToken**        | Revoked refresh token JTIs (for token rotation)           |

**Relationships:** User ↔ Role (M2M), Role ↔ Permission (M2M), User → KYCDocuments, User → Payments, Merchant → Payments, Merchant → WebhookSubscriptions → WebhookDeliveries.

---

## Authentication & Authorisation

- **JWT tokens** — HS256 algorithm, configurable expiry
  - Access token: 1 hour (default)
  - Refresh token: 30 days (default), with one-time-use rotation
- **Password policy** — minimum 8 characters, must include uppercase, lowercase, digit, and special character (`!@#$%^&*`)
- **Field encryption** — Fernet (AES-128-CBC) for sensitive fields like merchant settlement accounts
- **Rate limiting** — configurable per-endpoint (e.g. 10/min on signup, 20/min on login)
- **RBAC** — enforced via `@jwt_required` and `@roles_required()` decorators

### Default Roles & Permissions

| Role  | Permissions                                                                   |
| ----- | ----------------------------------------------------------------------------- |
| admin | All 13 permissions (users, KYC, payments, merchants, webhooks, audit)         |
| staff | users.read/write, kyc.upload/review, payments.create/read/process, audit.read |
| user  | users.read/write (own), kyc.upload, payments.create/read                      |

---

## Project Structure

```
app/
├── __init__.py              App factory, blueprint registration, CLI
├── config.py                Dev / Testing / Production configs
├── extensions.py            SQLAlchemy, Migrate, Limiter init
├── celery_app.py            Celery configuration
├── metrics.py               Custom Prometheus counters & histograms
├── api/v1/                  REST API endpoints
│   ├── auth.py              Signup, login, refresh, logout
│   ├── identity.py          Profile, users, KYC
│   ├── payments.py          Payments & token management
│   ├── merchants.py         Merchant onboarding
│   ├── webhooks.py          Webhook subscriptions
│   ├── admin.py             Admin stats, audit, user management
│   └── health.py            Health & readiness probes
├── models/                  SQLAlchemy models
│   ├── user.py              User, Role
│   ├── payment.py           Payment, PaymentToken
│   ├── merchant.py          Merchant
│   ├── kyc.py               KYCDocument
│   ├── audit.py             AuditLog
│   ├── permission.py        Permission
│   ├── revoked_token.py     RevokedToken
│   ├── webhook.py           WebhookSubscription, WebhookDelivery
│   └── __init__.py          Central imports
├── services/                Business logic layer
│   ├── identity_service.py  User signup, auth, roles
│   ├── payment_service.py   Payment processing
│   ├── merchant_service.py  Merchant management
│   ├── kyc_service.py       Document verification
│   ├── webhook_service.py   Event dispatch
│   └── audit_service.py     Immutable audit logging
├── middleware/
│   ├── auth.py              @jwt_required decorator
│   └── rbac.py              @roles_required decorator
├── utils/
│   ├── validators.py        Input validation (signup, payment, merchant)
│   ├── encryption.py        Fernet encrypt / decrypt helpers
│   └── errors.py            Custom HTTP exceptions
├── workers/
│   └── verification_worker.py  Celery tasks for KYC auto-verification
├── ui/                      Web frontend
│   ├── routes.py            11 page routes
│   ├── static/css/          Design system stylesheet
│   ├── static/js/api.js     JS API client with auto token refresh
│   └── templates/ui/        Jinja2 page templates
└── merchant_dashboard/      Merchant-facing dashboard (API-key auth)
    └── routes.py            Login, overview, stats

tests/                       pytest suite (26 tests)
├── conftest.py              Fixtures (app, client, auth/admin headers)
├── test_auth.py             Authentication tests
├── test_health.py           Health endpoint tests
├── test_identity.py         Profile & user management tests
├── test_merchants.py        Merchant onboarding tests
├── test_payments.py         Payment flow tests
└── test_integration.py      End-to-end integration tests

sdks/
├── python/                  Python SDK (elcorp_sdk)
└── node/                    Node.js / TypeScript SDK

migrations/                  Alembic migration scripts
k8s/                         Kubernetes deployment manifests
monitoring/                  Prometheus & Grafana configuration
scripts/                     Backup & restore scripts
docs/                        Full documentation
.github/workflows/           CI (lint + test + build) & Deploy pipelines
postman/                     Postman collection & environment
```

---

## Running Tests

```bash
# All tests
pytest -q

# With coverage
pytest --cov=app --cov-report=term-missing

# Specific module
pytest tests/test_payments.py -v
```

**26 tests** covering auth flows, identity management, KYC, payments, merchants, and integration scenarios.

### Load Testing

```bash
locust -f tests/load/locustfile.py --host http://localhost:5000
```

---

## CLI Commands

```bash
# Run database migrations
flask db upgrade

# Promote an existing user to admin
flask promote-admin user@example.com

# Start development server
flask run

# Start Celery worker
celery -A app.celery_app:celery worker --loglevel=info

# Start Celery beat scheduler
celery -A app.celery_app:celery beat --loglevel=info
```

---

## Docker

### Development

```bash
docker compose up --build
```

Services: API (Flask dev server), Celery Worker, Celery Beat, PostgreSQL, Redis.

### Production

```bash
docker compose -f docker-compose.production.yml up --build -d
```

Uses multi-stage build with Gunicorn (4 workers), non-root user, health checks, and restart policies.

---

## Kubernetes Deployment

Pre-built manifests in `k8s/`:

| Manifest                   | Description                                            |
| -------------------------- | ------------------------------------------------------ |
| `api-deployment.yaml`      | 2 replicas, readiness/liveness probes, resource limits |
| `worker-deployment.yaml`   | Celery worker + beat scheduler                         |
| `postgres-deployment.yaml` | PostgreSQL with persistent volume                      |
| `redis-deployment.yaml`    | Redis instance                                         |
| `configmap.yaml`           | Non-secret configuration                               |
| `secrets.yaml`             | SECRET_KEY, ENCRYPTION_KEY (base64)                    |
| `ingress.yaml`             | Nginx ingress with TLS (cert-manager)                  |

---

## Monitoring

### Prometheus Metrics

Custom application metrics exposed at `/metrics`:

| Metric              | Type      | Labels                   | Description                 |
| ------------------- | --------- | ------------------------ | --------------------------- |
| `payment_created`   | Counter   | currency, status         | Payments created            |
| `payment_processed` | Counter   | outcome                  | Payment processing results  |
| `kyc_uploads`       | Counter   | document_type            | KYC document uploads        |
| `auth_events`       | Counter   | event                    | Auth events (signup, login) |
| `api_errors`        | Counter   | status_code, endpoint    | API error responses         |
| `request_latency`   | Histogram | method, endpoint, status | Request duration (seconds)  |

### Configuration

- `monitoring/prometheus.yml` — scrape config for API, Celery, Postgres, Redis exporters
- Grafana dashboards available for import

---

## Environment Variables

Copy `.env.example` and fill in values:

| Variable                    | Required | Default                    | Description                            |
| --------------------------- | -------- | -------------------------- | -------------------------------------- |
| `SECRET_KEY`                | Yes      | —                          | Flask secret / JWT signing key         |
| `ENCRYPTION_KEY`            | Yes      | —                          | Fernet key for field encryption        |
| `DATABASE_URL`              | No       | `sqlite:///elcorp_dev.db`  | Database connection string             |
| `REDIS_URL`                 | No       | `redis://localhost:6379/0` | Redis connection                       |
| `CELERY_BROKER_URL`         | No       | Redis URL                  | Celery message broker                  |
| `JWT_ACCESS_TOKEN_EXPIRES`  | No       | `3600`                     | Access token lifetime (seconds)        |
| `JWT_REFRESH_TOKEN_EXPIRES` | No       | `2592000`                  | Refresh token lifetime (seconds)       |
| `UPLOAD_FOLDER`             | No       | `uploads`                  | KYC file upload directory              |
| `MAX_CONTENT_LENGTH`        | No       | `16777216`                 | Max upload size (bytes, default 16 MB) |
| `CORS_ORIGINS`              | No       | `*`                        | Allowed CORS origins                   |
| `RATELIMIT_DEFAULT`         | No       | `100/hour`                 | Default rate limit                     |

---

## Tech Stack

| Layer         | Technology                                          |
| ------------- | --------------------------------------------------- |
| Framework     | Flask 3.1.0                                         |
| ORM           | SQLAlchemy 2.0.36 + Flask-Migrate (Alembic)         |
| Auth          | PyJWT 2.10.1 + bcrypt 4.2.1                         |
| Encryption    | cryptography 44.0.0 (Fernet)                        |
| Task Queue    | Celery 5.4.0 + Redis 5.2.1                          |
| Monitoring    | prometheus-flask-exporter 0.23.1 + structlog 24.4.0 |
| Rate Limiting | Flask-Limiter 3.8.0                                 |
| Validation    | marshmallow 3.23.2 + email-validator 2.2.0          |
| Testing       | pytest 8.3.4 + pytest-cov + Locust 2.32.4           |
| Linting       | Ruff 0.8.6                                          |
| Containers    | Docker + Docker Compose                             |
| Orchestration | Kubernetes (manifests provided)                     |
| CI/CD         | GitHub Actions                                      |

---

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Dashboard Guide](docs/DASHBOARD_GUIDE.md)
- [Operations Guide](docs/OPERATIONS_GUIDE.md)
- [Mobile Integration](docs/MOBILE_INTEGRATION.md)
- [Service Request System](docs/SERVICE_REQUEST_SYSTEM.md)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

See [SECURITY.md](SECURITY.md) for the security policy and responsible disclosure process.

## License

Proprietary — Elcorp Namibia. All rights reserved.
| `REDIS_URL` | no | `redis://localhost:6379/0` | Redis for Celery / rate limits |
| `FLASK_ENV` | no | `development` | `development` / `testing` / `production` |

## License

Proprietary — Elcorp Namibia. All rights reserved.
