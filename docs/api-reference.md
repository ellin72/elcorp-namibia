# Elcorp API Reference — v1

Base URL: `http://localhost:5000/api/v1`

All authenticated endpoints require the header `Authorization: Bearer <access_token>`.

---

## Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Liveness probe |
| GET | `/health/ready` | No | Readiness (DB) probe |

---

## Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/signup` | No | Create account |
| POST | `/auth/login` | No | Obtain tokens |
| POST | `/auth/refresh` | No | Refresh access token |
| GET | `/auth/validate` | Yes | Validate current token |
| POST | `/auth/logout` | Yes | Placeholder logout |

### POST /auth/signup

```json
{
  "email": "user@example.na",
  "password": "StrongP4ss!",
  "first_name": "Jane",
  "last_name": "Doe"
}
```

**Response 201**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user": { "id": "uuid", "email": "user@example.na", "is_verified": false, ... }
}
```

### POST /auth/login

```json
{ "email": "user@example.na", "password": "StrongP4ss!" }
```

**Response 200** — same shape as signup.

### POST /auth/refresh

```json
{ "refresh_token": "eyJ..." }
```

**Response 200**

```json
{ "access_token": "eyJ..." }
```

---

## Identity

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| GET | `/me` | Yes | any | Get own profile |
| PUT | `/me` | Yes | any | Update own profile |
| GET | `/users` | Yes | admin | List all users |
| GET | `/users/:id` | Yes | admin | Get user by ID |

### PUT /me

Accepts any subset of: `first_name`, `last_name`, `phone`, `date_of_birth`, `national_id`, `address`.

---

## KYC

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| POST | `/kyc/upload` | Yes | any | Upload document |
| GET | `/kyc/documents` | Yes | any | List own documents |
| POST | `/kyc/:id/review` | Yes | admin, staff | Approve / reject |
| GET | `/kyc/pending` | Yes | admin, staff | List pending docs |

### POST /kyc/upload (`multipart/form-data`)

| Field | Type | Required | Values |
|-------|------|----------|--------|
| file | file | yes | image/pdf |
| document_type | string | yes | `national_id`, `passport`, `drivers_license`, `proof_of_address`, `selfie` |

### POST /kyc/:id/review

```json
{ "decision": "approved" }
```

or

```json
{ "decision": "rejected", "reason": "Document is expired" }
```

---

## Payments

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| POST | `/payments/tokens` | Yes | any | Tokenise instrument |
| POST | `/payments` | Yes | any | Create payment |
| POST | `/payments/:id/process` | Yes | any | Process (sandbox) |
| GET | `/payments/:id` | Yes | any | Get payment details |
| GET | `/payments` | Yes | any | List own payments |
| POST | `/payments/simulate-payout` | Yes | admin | Simulate merchant payout |

### POST /payments/tokens

```json
{ "instrument_type": "card", "last_four": "4242" }
```

### POST /payments

```json
{
  "merchant_id": "uuid",
  "amount": 5000,
  "currency": "NAD",
  "description": "Clinic visit"
}
```

Amount is in **cents** (5000 = NAD 50.00).

### POST /payments/:id/process

No body needed. Returns updated payment with `status`, `gateway_ref`.

### POST /payments/simulate-payout

```json
{ "merchant_id": "uuid", "amount": 10000, "currency": "NAD" }
```

---

## Merchants

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| POST | `/merchants` | Yes | admin | Onboard merchant |
| GET | `/merchants` | Yes | admin | List merchants |
| GET | `/merchants/:id` | Yes | admin, staff | Get merchant |
| PUT | `/merchants/:id` | Yes | admin | Update merchant |
| POST | `/merchants/:id/deactivate` | Yes | admin | Deactivate |

### POST /merchants

```json
{
  "name": "Pilot Clinic",
  "contact_email": "clinic@pilot.na",
  "business_type": "clinic",
  "settlement_bank": "FNB Namibia",
  "settlement_account": "123456789"
}
```

**Response 201** includes `api_key` (shown once).

---

## Admin

| Method | Path | Auth | Roles | Description |
|--------|------|------|-------|-------------|
| GET | `/admin/audit-logs` | Yes | admin | Paginated audit trail |
| GET | `/admin/stats` | Yes | admin | System summary |
| PUT | `/admin/users/:id/roles` | Yes | admin | Set user roles |
| POST | `/admin/users/:id/deactivate` | Yes | admin | Deactivate user |

### GET /admin/audit-logs?page=1&per_page=50

Optional query filters: `user_id`, `action`, `entity_type`.

### PUT /admin/users/:id/roles

```json
{ "roles": ["user", "staff"] }
```

---

## Error Format

All errors return:

```json
{ "error": "Short title", "message": "Detailed message" }
```

Common HTTP codes: `400`, `401`, `403`, `404`, `409`, `422`, `429`, `500`.
