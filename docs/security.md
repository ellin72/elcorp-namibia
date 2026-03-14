# Security

## Authentication

- **JWT access tokens** — short-lived (configurable, default 1 hour), signed with HS256
- **JWT refresh tokens** — longer-lived (default 30 days), used to obtain new access tokens
- Passwords hashed with **bcrypt** (cost factor 12)

## Authorisation (RBAC)

Three roles enforced at the API layer:

| Role  | Access                                                              |
| ----- | ------------------------------------------------------------------- |
| user  | Own profile, KYC, payments                                          |
| staff | + KYC review, merchant viewing                                      |
| admin | + user management, merchant onboarding, audit logs, role assignment |

Role checks use the `@roles_required()` decorator applied **after** JWT authentication.

## Encryption at Rest

- Sensitive fields (e.g., merchant settlement account numbers) are encrypted with **Fernet (AES-128-CBC)** using the `ENCRYPTION_KEY` environment variable.
- The encryption key must be generated with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and stored securely.

## Rate Limiting

- Sign-up: **10 requests/minute** per IP
- Login: **20 requests/minute** per IP
- General API: **200 requests/minute** per IP (configurable)

Implemented via Flask-Limiter with in-memory storage (Redis in production).

## Audit Trail

Every significant action is logged to the `audit_logs` table:

- User ID (if authenticated)
- Action name (e.g., `user.signup`, `kyc.review`, `payment.process`)
- Entity type and ID
- IP address and User-Agent
- Timestamp (UTC)

Admin access via `GET /api/v1/admin/audit-logs`.

## Input Validation

- Email validated with the `email-validator` library
- Passwords must meet complexity requirements (8+ chars, mixed case, digit, special char)
- Phone numbers validated with regex (`+` followed by 7–15 digits)
- File uploads restricted to known MIME types and document type enum
- All user input is parameterised in SQL queries (SQLAlchemy ORM) — no raw SQL

## File Uploads

- Files stored in a configurable upload directory (default `uploads/kyc/`)
- Each file is saved with a UUID filename to prevent path traversal
- SHA-256 hash computed and stored for integrity verification
- Original filename stored separately for display purposes

## CORS

- Configurable allowed origins via `CORS_ORIGINS` environment variable
- Defaults to `*` in development; should be restricted in production

## Environment Variables

All secrets are loaded from environment variables — never committed to the repository.
See `.env.example` for the full list.
