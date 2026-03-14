"""Tests for authentication endpoints."""

import pytest


class TestSignup:
    def test_signup_success(self, client):
        resp = client.post("/api/v1/auth/signup", json={
            "email": "new@elcorp.na",
            "password": "Secure1234!",
            "first_name": "New",
            "last_name": "User",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "new@elcorp.na"

    def test_signup_duplicate(self, client):
        payload = {
            "email": "dup@elcorp.na",
            "password": "Secure1234!",
            "first_name": "Dup",
            "last_name": "User",
        }
        client.post("/api/v1/auth/signup", json=payload)
        resp = client.post("/api/v1/auth/signup", json=payload)
        assert resp.status_code == 409

    def test_signup_weak_password(self, client):
        resp = client.post("/api/v1/auth/signup", json={
            "email": "weak@elcorp.na",
            "password": "short",
            "first_name": "Weak",
            "last_name": "User",
        })
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        client.post("/api/v1/auth/signup", json={
            "email": "login@elcorp.na",
            "password": "Secure1234!",
            "first_name": "Login",
            "last_name": "User",
        })
        resp = client.post("/api/v1/auth/login", json={
            "email": "login@elcorp.na",
            "password": "Secure1234!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()

    def test_login_bad_password(self, client):
        client.post("/api/v1/auth/signup", json={
            "email": "login2@elcorp.na",
            "password": "Secure1234!",
            "first_name": "Login",
            "last_name": "User",
        })
        resp = client.post("/api/v1/auth/login", json={
            "email": "login2@elcorp.na",
            "password": "wrong",
        })
        assert resp.status_code == 404


class TestTokenRefresh:
    def test_refresh(self, client):
        resp = client.post("/api/v1/auth/signup", json={
            "email": "refresh@elcorp.na",
            "password": "Secure1234!",
            "first_name": "Ref",
            "last_name": "User",
        })
        refresh_token = resp.get_json()["refresh_token"]
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.get_json()


class TestValidate:
    def test_validate(self, client, auth_headers):
        resp = client.get("/api/v1/auth/validate", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.get_json()["valid"] is True
