"""Tests for merchant endpoints."""

import pytest


class TestMerchantOnboarding:
    def test_onboard_merchant(self, client, admin_headers):
        resp = client.post("/api/v1/merchants", headers=admin_headers, json={
            "name": "Pilot Clinic",
            "contact_email": "pilot@clinic.na",
            "business_type": "clinic",
            "registration_number": "REG-001",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Pilot Clinic"
        assert data["api_key"].startswith("sk_sandbox_")

    def test_onboard_requires_admin(self, client, auth_headers):
        resp = client.post("/api/v1/merchants", headers=auth_headers, json={
            "name": "Bad Attempt",
            "contact_email": "bad@example.com",
        })
        assert resp.status_code == 403

    def test_list_merchants(self, client, admin_headers):
        resp = client.get("/api/v1/merchants", headers=admin_headers)
        assert resp.status_code == 200

    def test_deactivate_merchant(self, client, admin_headers):
        resp = client.post("/api/v1/merchants", headers=admin_headers, json={
            "name": "To Deactivate",
            "contact_email": "deact@clinic.na",
        })
        mid = resp.get_json()["id"]
        resp = client.post(f"/api/v1/merchants/{mid}/deactivate", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "deactivated"
