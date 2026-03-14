"""Tests for payment endpoints."""

import pytest


@pytest.fixture()
def merchant_id(client, admin_headers):
    """Create a merchant and return its ID."""
    resp = client.post("/api/v1/merchants", headers=admin_headers, json={
        "name": "Test Clinic",
        "contact_email": "clinic@test.na",
        "business_type": "clinic",
    })
    return resp.get_json()["id"]


class TestTokenisation:
    def test_create_token(self, client, auth_headers):
        resp = client.post("/api/v1/payments/tokens", headers=auth_headers, json={
            "instrument_type": "card",
            "last_four": "4242",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["last_four"] == "4242"
        assert data["token"].startswith("tok_")


class TestPayments:
    def test_create_and_process_payment(self, client, auth_headers, merchant_id):
        # create
        resp = client.post("/api/v1/payments", headers=auth_headers, json={
            "merchant_id": merchant_id,
            "amount": 5000,
            "currency": "NAD",
            "description": "Clinic visit",
        })
        assert resp.status_code == 201
        payment = resp.get_json()
        assert payment["status"] == "pending"

        # process
        resp = client.post(
            f"/api/v1/payments/{payment['id']}/process",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "completed"

    def test_create_payment_invalid_merchant(self, client, auth_headers):
        resp = client.post("/api/v1/payments", headers=auth_headers, json={
            "merchant_id": "nonexistent",
            "amount": 100,
            "currency": "NAD",
        })
        assert resp.status_code == 404

    def test_list_payments(self, client, auth_headers):
        resp = client.get("/api/v1/payments", headers=auth_headers)
        assert resp.status_code == 200
        assert "items" in resp.get_json()


class TestPayout:
    def test_simulate_payout(self, client, auth_headers, merchant_id):
        resp = client.post("/api/v1/payments/simulate-payout", headers=auth_headers, json={
            "merchant_id": merchant_id,
            "amount": 10000,
            "currency": "NAD",
        })
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "settled"
