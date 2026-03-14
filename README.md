# Elcorp — Digital Identity & Payments MVP

Production-grade API for digital identity verification and payment processing in Namibia.

## What's in this MVP

| Epic                     | Delivered                                                                                    |
| ------------------------ | -------------------------------------------------------------------------------------------- |
| **Identity Core**        | Signup, profile, KYC upload, automated + manual verification, audit trail                    |
| **Payments Sandbox**     | Tokenised instruments, payment creation & processing, merchant onboarding, simulated payouts |
| **Developer Experience** | REST API, Postman collection, Python SDK, Node SDK, sample CLI app                           |
| **Security**             | JWT auth, bcrypt passwords, Fernet field-level encryption, RBAC, rate limiting               |
| **CI/CD**                | GitHub Actions (lint → test → build → deploy), Docker images, K8s manifests                  |
| **Monitoring**           | Prometheus metrics, Grafana dashboard, alerting rules                                        |

## Quick Start

### Local (SQLite, no Docker)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env
flask db upgrade
flask run
```

### Docker Compose

```bash
docker compose up --build
```

API: `http://localhost:5000/api/v1`

### First API calls

```bash
# Health
curl http://localhost:5000/api/v1/health

# Sign up
curl -X POST http://localhost:5000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@elcorp.na","password":"Demo1234!","first_name":"Demo","last_name":"User"}'

# Authenticated request
curl http://localhost:5000/api/v1/me -H "Authorization: Bearer <token>"
```

## Project Structure

```
app/                 Flask application
├── api/v1/          REST endpoints
├── models/          SQLAlchemy models
├── services/        Business logic
├── middleware/       JWT, RBAC
├── utils/           Encryption, validation, errors
└── workers/         Celery background tasks
tests/               pytest suite (23 tests)
sdks/python/         Python SDK
sdks/node/           Node.js/TypeScript SDK
sample-app/          Demo CLI
postman/             Postman collection & environment
docs/                Full documentation
k8s/                 Kubernetes manifests
monitoring/          Prometheus + Grafana configs
.github/workflows/   CI (lint+test) & Deploy pipelines
```

## Running Tests

```bash
pytest -q
```

## Documentation

- [Getting Started](docs/getting-started.md)
- [API Reference](docs/api-reference.md)
- [Identity Guide](docs/identity-guide.md)
- [Payments Guide](docs/payments-guide.md)
- [Security](docs/security.md)
- [Architecture](docs/architecture.md)

## Pilot Onboarding

See [PILOT_ONBOARDING.md](PILOT_ONBOARDING.md) for a step-by-step guide to onboard a clinic and payment partner.

## Environment Variables

Copy `.env.example` and fill in values. Key variables:

| Variable         | Required | Default                    | Description                              |
| ---------------- | -------- | -------------------------- | ---------------------------------------- |
| `SECRET_KEY`     | yes      | —                          | Flask secret / JWT signing key           |
| `ENCRYPTION_KEY` | yes      | —                          | Fernet key for field encryption          |
| `DATABASE_URL`   | no       | `sqlite:///dev.db`         | Database connection string               |
| `REDIS_URL`      | no       | `redis://localhost:6379/0` | Redis for Celery / rate limits           |
| `FLASK_ENV`      | no       | `development`              | `development` / `testing` / `production` |

## License

Proprietary — Elcorp Namibia. All rights reserved.
