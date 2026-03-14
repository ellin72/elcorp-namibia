# Elcorp Node.js SDK

TypeScript/JavaScript client for the Elcorp Digital Identity & Payments API.

## Install

```bash
cd sdks/node
npm install
npm run build
```

## Quick start

```typescript
import { ElcorpClient } from "elcorp-sdk";

const client = new ElcorpClient("http://localhost:5000/api/v1");

// Sign up
const auth = await client.signup(
  "alice@example.com",
  "Secure1234!",
  "Alice",
  "Smith",
);
console.log(auth.user);

// Create a payment
const payment = await client.createPayment(
  "merchant-id",
  5000,
  "NAD",
  "Clinic visit",
);
const result = await client.processPayment(payment.id);
console.log(result.status); // "completed"
```
