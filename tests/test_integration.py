"""Integration test — end-to-end: signup → KYC → verify → payment."""

import io
import pytest


class TestEndToEnd:
    def test_full_flow(self, client, admin_headers):
        # 1. User signs up
        resp = client.post("/api/v1/auth/signup", json={
            "email": "e2e@elcorp.na",
            "password": "E2eTest1234!",
            "first_name": "End",
            "last_name": "User",
        })
        assert resp.status_code == 201
        user_token = resp.get_json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # 2. Upload KYC document
        resp = client.post(
            "/api/v1/kyc/upload",
            headers=user_headers,
            data={
                "document_type": "national_id",
                "file": (io.BytesIO(b"fake national id scan"), "national_id.png"),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        doc_id = resp.get_json()["id"]

        # 3. Admin reviews and approves KYC
        resp = client.post(
            f"/api/v1/kyc/{doc_id}/review",
            headers=admin_headers,
            json={"decision": "approved"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "approved"

        # 4. Check user is now verified
        resp = client.get("/api/v1/me", headers=user_headers)
        assert resp.get_json()["is_verified"] is True

        # 5. Admin onboards a merchant
        resp = client.post("/api/v1/merchants", headers=admin_headers, json={
            "name": "E2E Clinic",
            "contact_email": "e2e@clinic.na",
            "business_type": "clinic",
        })
        assert resp.status_code == 201
        merchant_id = resp.get_json()["id"]

        # 6. User creates a payment
        resp = client.post("/api/v1/payments", headers=user_headers, json={
            "merchant_id": merchant_id,
            "amount": 15000,
            "currency": "NAD",
            "description": "Clinic consultation",
        })
        assert resp.status_code == 201
        payment_id = resp.get_json()["id"]

        # 7. Process (sandbox gateway)
        resp = client.post(
            f"/api/v1/payments/{payment_id}/process",
            headers=user_headers,
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "completed"

        # 8. Admin checks audit logs
        resp = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
        assert resp.status_code == 200
        logs = resp.get_json()["items"]
        actions = [log["action"] for log in logs]
        assert "user.signup" in actions
        assert "payment.completed" in actions
