# Payments Guide

## Overview

The Elcorp Payments Sandbox lets you:

1. **Tokenise** a payment instrument (card, mobile money, etc.)
2. **Create** a payment against a merchant
3. **Process** the payment through the sandbox gateway
4. **Simulate payouts** to merchants

All amounts are in **cents** (e.g., `5000` = NAD 50.00).

## Payment Flow

```
User ─ Create Token ─► Token stored
  │
  ├─ Create Payment ──► status: pending
  │
  └─ Process Payment ──► Sandbox gateway ──► status: completed
                                              (gateway_ref assigned)
```

## 1. Tokenise a Payment Instrument

```http
POST /api/v1/payments/tokens
Authorization: Bearer <token>
Content-Type: application/json

{
  "instrument_type": "card",
  "last_four": "4242"
}
```

This stores a reference token; no real card data is stored.

## 2. Create a Payment

```http
POST /api/v1/payments
Authorization: Bearer <token>
Content-Type: application/json

{
  "merchant_id": "<uuid>",
  "amount": 7500,
  "currency": "NAD",
  "description": "Clinic consultation"
}
```

The payment starts in `pending` status with a unique reference like `PAY-a1b2c3d4`.

## 3. Process the Payment

```http
POST /api/v1/payments/<payment_id>/process
Authorization: Bearer <token>
```

In sandbox mode, the gateway instantly approves the payment and assigns a `gateway_ref`.

Possible statuses after processing: `completed`, `failed`.

## 4. Simulate a Payout

Admin-only endpoint to simulate funds transfer to a merchant:

```http
POST /api/v1/payments/simulate-payout
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "merchant_id": "<uuid>",
  "amount": 50000,
  "currency": "NAD"
}
```

Returns a sandbox payout reference.

## Currency

Currently supported: `NAD` (Namibian Dollar). The `currency` field is always required.

## Error Handling

| Code | Meaning |
|------|---------|
| 400 | Invalid payment data |
| 404 | Payment or merchant not found |
| 409 | Payment already processed |
| 422 | Validation failure (missing fields, bad amount) |

## Sandbox vs Production

In sandbox mode (`SANDBOX_MODE=true`, the default), the payment gateway:
- Instantly approves all payments
- Generates fake gateway references (`sandbox-<uuid>`)
- Simulates payouts without real fund movement

Production mode will integrate with real payment gateways (future sprint).
