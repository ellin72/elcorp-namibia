# Getting Started

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or use SQLite for local dev)
- Redis 7+ (for Celery workers)

## Quick Start (local, SQLite)

```bash
# Clone the repo
git clone https://github.com/elcorp/elcorp-namibia.git
cd elcorp-namibia

# Create venv and install deps
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

# Copy env template
cp .env.example .env
# Edit .env as needed — defaults work for SQLite dev mode

# Initialise database
flask db upgrade

# Run
flask run
```

API is now live at `http://localhost:5000/api/v1`.

## Quick Start (Docker)

```bash
docker compose up --build
```

This starts the API, a Postgres database, a Redis instance, and a Celery worker.

## First Requests

```bash
# 1. Health check
curl http://localhost:5000/api/v1/health

# 2. Sign up
curl -X POST http://localhost:5000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@elcorp.na","password":"Demo1234!","first_name":"Demo","last_name":"User"}'

# 3. Use the access_token from the response for authenticated requests
curl http://localhost:5000/api/v1/me \
  -H "Authorization: Bearer <access_token>"
```

## Next Steps

- [API Reference](api-reference.md) — every endpoint detailed
- [Identity Guide](identity-guide.md) — signup, KYC, verification
- [Payments Guide](payments-guide.md) — tokenise, pay, payout
- [Security](security.md) — encryption, RBAC, audit trail
- [Architecture](architecture.md) — system design overview
