# Elcorp Python SDK

Lightweight Python client for the Elcorp Digital Identity & Payments API.

## Install

```bash
pip install -e sdks/python
```

## Quick start

```python
from elcorp_sdk import ElcorpClient

client = ElcorpClient(base_url="http://localhost:5000/api/v1")

# Sign up
result = client.signup("alice@example.com", "Secure1234!", "Alice", "Smith")
print(result["user"]["id"])

# Upload KYC document
doc = client.upload_kyc("national_id", "/path/to/id.png")

# Create a payment
payment = client.create_payment(merchant_id="...", amount=5000, currency="NAD")
processed = client.process_payment(payment["id"])
print(processed["status"])  # "completed"
```
