# Pilot Onboarding Guide

Step-by-step guide to bring a clinic and payment partner into the Elcorp sandbox.

---

## Prerequisites

- API running (local or Docker) — see [README](README.md)
- Admin account created and assigned the `admin` role
- Postman (optional, but helpful) — import `postman/elcorp-sandbox.postman_collection.json`

---

## Step 1 — Create the Admin Account

```bash
# Sign up
curl -X POST http://localhost:5000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@elcorp.na","password":"Admin1234!","first_name":"Admin","last_name":"Super"}'
```

Manually promote to admin (run in Flask shell or via a seed script):

```python
from app import create_app, db
from app.models import User, Role

app = create_app("development")
with app.app_context():
    from app.services.identity_service import seed_roles
    seed_roles()  # creates user, staff, admin roles if missing
    user = User.query.filter_by(email="admin@elcorp.na").first()
    admin_role = Role.query.filter_by(name="admin").first()
    if admin_role not in user.roles:
        user.roles.append(admin_role)
    db.session.commit()
    print(f"Admin ready: {user.email}")
```

---

## Step 2 — Onboard the Clinic (Merchant)

Login as admin and onboard the pilot clinic:

```bash
# Login as admin
TOKEN=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@elcorp.na","password":"Admin1234!"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Onboard clinic
curl -X POST http://localhost:5000/api/v1/merchants \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Windhoek Wellness Clinic",
    "contact_email": "billing@windhoekwellness.na",
    "business_type": "clinic",
    "settlement_bank": "FNB Namibia",
    "settlement_account": "62000012345"
  }'
```

**Save the `api_key`** from the response — it is shown only once.

Record the `merchant_id` for payment testing.

---

## Step 3 — Register a Patient (End-User)

```bash
curl -X POST http://localhost:5000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patient@example.na",
    "password": "Patient1234!",
    "first_name": "Aune",
    "last_name": "Shikongo"
  }'
```

---

## Step 4 — KYC Verification

Upload ID document:

```bash
PATIENT_TOKEN="<patient_access_token>"

curl -X POST http://localhost:5000/api/v1/kyc/upload \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -F "document_type=national_id" \
  -F "file=@/path/to/id_scan.png"
```

Admin reviews:

```bash
# List pending
curl http://localhost:5000/api/v1/kyc/pending \
  -H "Authorization: Bearer $TOKEN"

# Approve (use doc_id from response)
curl -X POST http://localhost:5000/api/v1/kyc/<doc_id>/review \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"decision": "approved"}'
```

Patient is now **verified** and can make payments.

---

## Step 5 — Test a Payment

```bash
# Create payment
curl -X POST http://localhost:5000/api/v1/payments \
  -H "Authorization: Bearer $PATIENT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "<merchant_id>",
    "amount": 35000,
    "currency": "NAD",
    "description": "Consultation fee"
  }'

# Process it (use payment_id from response)
curl -X POST http://localhost:5000/api/v1/payments/<payment_id>/process \
  -H "Authorization: Bearer $PATIENT_TOKEN"
```

---

## Step 6 — Simulate Payout to Clinic

```bash
curl -X POST http://localhost:5000/api/v1/payments/simulate-payout \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "<merchant_id>",
    "amount": 35000,
    "currency": "NAD"
  }'
```

---

## Step 7 — Review Audit Trail

```bash
curl "http://localhost:5000/api/v1/admin/audit-logs?per_page=20" \
  -H "Authorization: Bearer $TOKEN"
```

Every action — signup, KYC review, payment processing — is logged.

---

## Pilot Checklist

- [ ] Admin account created and promoted
- [ ] Clinic merchant onboarded, API key stored securely
- [ ] Test patient signed up
- [ ] KYC document uploaded and approved
- [ ] Payment created and processed
- [ ] Payout simulated
- [ ] Audit trail reviewed
- [ ] Postman collection imported and variables set
- [ ] SDK integrated into clinic POS / frontend (if applicable)

---

## Support

For issues during the pilot, check the audit logs and API health endpoint first:

```bash
curl http://localhost:5000/api/v1/health/ready
```

Logs are structured JSON (stdout) — pipe through `jq` for readability.
