"""Tests for identity / profile / KYC endpoints."""

import io
import pytest


class TestProfile:
    def test_get_me(self, client, auth_headers):
        resp = client.get("/api/v1/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["email"] == "test@elcorp.na"

    def test_update_me(self, client, auth_headers):
        resp = client.put("/api/v1/me", headers=auth_headers, json={
            "first_name": "Updated",
            "phone": "+264811234567",
        })
        assert resp.status_code == 200
        assert resp.get_json()["first_name"] == "Updated"


class TestKYC:
    def test_upload_document(self, client, auth_headers):
        data = {
            "document_type": "national_id",
            "file": (io.BytesIO(b"fake image bytes"), "id.png"),
        }
        resp = client.post(
            "/api/v1/kyc/upload",
            headers=auth_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 201
        assert resp.get_json()["document_type"] == "national_id"

    def test_upload_invalid_type(self, client, auth_headers):
        data = {
            "document_type": "invalid_type",
            "file": (io.BytesIO(b"fake"), "doc.png"),
        }
        resp = client.post(
            "/api/v1/kyc/upload",
            headers=auth_headers,
            data=data,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 422

    def test_list_documents(self, client, auth_headers):
        resp = client.get("/api/v1/kyc/documents", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)


class TestUserManagement:
    def test_list_users_requires_admin(self, client, auth_headers):
        resp = client.get("/api/v1/users", headers=auth_headers)
        assert resp.status_code == 403

    def test_list_users_as_admin(self, client, admin_headers):
        resp = client.get("/api/v1/users", headers=admin_headers)
        assert resp.status_code == 200
        assert "items" in resp.get_json()
