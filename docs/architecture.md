# Architecture Overview

Elcorp Namibia is a Flask-based modular application with the following components:

- Web app: Flask + Jinja2 templates
- Database: PostgreSQL (SQLAlchemy, Alembic for migrations)
- Background jobs: Celery + Redis (recommended)
- Auth: Flask-Login, role-based access, TOTP 2FA (otp_secret stored in DB; consider vaulting/encryption)
- Audit: AuditLog and PasswordResetAudit tables with DB-backed audit trail
- Observability: Prometheus metrics, Sentry for error tracking
- CI/CD: GitHub Actions for CI, image builds pushed to GHCR, deployments via kubectl/helm or ECS

Operational notes:

- Add a secret manager to hold OTP secrets and DB credentials in prod.
- Use canary/blue-green deploys for zero-downtime releases.
