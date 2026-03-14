# Identity Guide

## Overview

Elcorp's Identity Core manages the full user lifecycle:

1. **Sign up** — email + password, get JWT tokens
2. **Profile** — update personal info, phone, national ID, address
3. **KYC upload** — submit documents (national ID, passport, selfie, etc.)
4. **Verification** — automated background checks + admin review
5. **Audit** — every action is logged immutably

## User Lifecycle

```
Anonymous → Sign Up → Unverified User → Upload KYC → Pending Review
                                                     ↓
                                              Admin Approve → Verified User
                                              Admin Reject  → Resubmit KYC
```

## Sign Up

```http
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "jane@example.na",
  "password": "Secure1234!",
  "first_name": "Jane",
  "last_name": "Doe"
}
```

Password requirements:

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (`!@#$%^&*`)

## Profile Management

Update profile fields (authenticated):

```http
PUT /api/v1/me
Authorization: Bearer <token>
Content-Type: application/json

{
  "phone": "+264811234567",
  "national_id": "NAM1234567890",
  "address": "12 Independence Ave, Windhoek"
}
```

## KYC Document Upload

Upload a document image or PDF:

```http
POST /api/v1/kyc/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

document_type = national_id
file = @document.png
```

Supported `document_type` values:

- `national_id`
- `passport`
- `drivers_license`
- `proof_of_address`
- `selfie`

Allowed MIME types: `image/jpeg`, `image/png`, `application/pdf`.

Files are stored with a SHA-256 hash for integrity verification.

## Verification Workflow

1. User uploads one or more KYC documents.
2. A background worker (`verification_worker`) runs automated checks:
   - File hash present?
   - Mime type valid?
3. Admin or staff member reviews pending documents.
4. On approval, the system automatically updates the user's `verification_status` to `verified` if **all** their documents are approved.

### Admin Review

```http
POST /api/v1/kyc/<doc_id>/review
Authorization: Bearer <admin_token>
Content-Type: application/json

{ "decision": "approved" }
```

Or reject:

```json
{ "decision": "rejected", "reason": "Document expired" }
```

## Roles

| Role    | Capabilities                                                             |
| ------- | ------------------------------------------------------------------------ |
| `user`  | Sign up, manage profile, upload KYC, make payments                       |
| `staff` | Review KYC documents, view merchant details                              |
| `admin` | All staff capabilities + manage users, merchants, roles, view audit logs |
