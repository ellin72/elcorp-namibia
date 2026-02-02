# Developer Quick Start Guide

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Node.js 18+
- Git

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/ellin72/elcorp-namibia.git
cd elcorp-namibia
```

### 2. Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values (optional for local dev)
# Defaults are provided for local development
```

### 3. Start Services with Docker Compose

```bash
# Start all services (PostgreSQL, Redis, Backend, Frontend, Celery)
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Stop services
docker-compose -f docker-compose.dev.yml down
```

### 4. Initialize Database

```bash
# Create migration (if needed)
docker-compose -f docker-compose.dev.yml exec backend flask db migrate -m "Initial migration"

# Apply migration
docker-compose -f docker-compose.dev.yml exec backend flask db upgrade
```

### 5. Access the Application

- **Frontend**: http://localhost:5173
- **API**: http://localhost:5000/api/v1
- **API Docs**: http://localhost:5000/api/v1/docs (Swagger)
- **Redis Commander** (optional): http://localhost:8081

---

## Local Development (Without Docker)

### Backend Setup

```bash
# Create virtual environment
python -m venv venv

# Activate venv
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_ENV=development
export DATABASE_URL=sqlite:///elcorp.db
# (or use .env file)

# Run migrations
flask db upgrade

# Start Flask server
flask run
# Server runs at http://localhost:5000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# Frontend runs at http://localhost:5173
```

---

## Common Commands

### Database

```bash
# Create new migration
flask db migrate -m "Add new field"

# Apply migrations
flask db upgrade

# Rollback last migration
flask db downgrade

# Reset database (development only)
flask db downgrade base
flask db upgrade
```

### Testing

```bash
# Run all tests
pytest

# Run specific test
pytest backend/tests/unit/identity/test_user_aggregate.py

# Run with coverage
pytest --cov=backend/src --cov-report=html

# Run integration tests
pytest backend/tests/integration/
```

### Linting & Formatting

```bash
# Format code
black backend/src tests

# Check imports
isort backend/src tests

# Lint
flake8 backend/src tests

# Type checking
mypy backend/src
```

### Celery Tasks

```bash
# Start worker
celery -A src.elcorp.celery_app worker --loglevel=info

# Start beat scheduler
celery -A src.elcorp.celery_app beat --loglevel=info

# Monitor tasks (requires flower)
pip install flower
celery -A src.elcorp.celery_app flower
# Access at http://localhost:5555
```

---

## Architecture Overview

The application uses **Domain-Driven Design (DDD)** with a **Hexagonal (Ports & Adapters)** architecture:

```
backend/src/elcorp/
├── shared/              # Shared kernel (all contexts use this)
│   ├── domain/         # Exceptions, value objects, events
│   ├── infrastructure/ # Repositories, audit logging, database
│   ├── security/       # JWT, password hashing, encryption
│   └── util/           # Validators, pagination, logging
├── identity/            # Identity bounded context (user management)
│   ├── domain/         # User aggregate, repositories
│   ├── application/    # DTOs, commands, handlers
│   ├── infrastructure/ # SQLAlchemy models, mappers
│   └── interfaces/     # Flask routes, API endpoints
├── payments/            # Future: Payments context
├── governance/          # Future: Governance context
├── compliance/          # Future: Compliance context
├── jobs/               # Celery async tasks
└── config.py           # Application configuration
```

---

## Key Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend | Flask 3.0+ | Web framework |
| Database | PostgreSQL | Persistent data store |
| ORM | SQLAlchemy 2.0 | Database abstraction |
| Auth | JWT + Device Tokens | Secure authentication |
| Cache | Redis | Session and data caching |
| Queue | Celery + Redis | Async job processing |
| Frontend | React 18 + Vite | Modern UI framework |
| Testing | pytest | Test framework |
| Docker | Docker Compose | Local development environment |

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :5000  # Backend
lsof -i :5173  # Frontend
lsof -i :5432  # PostgreSQL

# Kill process
kill -9 <PID>
```

### Database Connection Error

```bash
# Check PostgreSQL is running
docker-compose -f docker-compose.dev.yml ps postgres

# Restart PostgreSQL
docker-compose -f docker-compose.dev.yml restart postgres

# Check logs
docker-compose -f docker-compose.dev.yml logs postgres
```

### Redis Connection Error

```bash
# Check Redis is running
docker-compose -f docker-compose.dev.yml ps redis

# Test Redis connection
redis-cli ping

# Restart Redis
docker-compose -f docker-compose.dev.yml restart redis
```

---

## Next Steps

1. Review [ARCHITECTURE_PRODUCTION.md](../ARCHITECTURE_PRODUCTION.md) for system design
2. Read [REFACTORING_IMPLEMENTATION_GUIDE.md](../REFACTORING_IMPLEMENTATION_GUIDE.md) for code structure
3. Check [SECURITY_HARDENING_GUIDE.md](../SECURITY_HARDENING_GUIDE.md) for security controls
4. See [DEPLOYMENT_OPERATIONS_GUIDE.md](../DEPLOYMENT_OPERATIONS_GUIDE.md) for production deployment

---

## Getting Help

- Check existing documentation in `/docs`
- Review test examples in `/backend/tests`
- Check API examples in `/backend/src/elcorp/identity/interfaces`
- Ask team lead or create GitHub issue

**Happy coding! 🚀**
