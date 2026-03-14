"""Locust load-test suite for Elcorp Digital Identity & Payments API.

Run:
    locust -f tests/load/locustfile.py --host http://127.0.0.1:5000

Then open http://localhost:8089 to configure users/ramp and start the test.
"""

from __future__ import annotations

import random
import string
import uuid

from locust import HttpUser, between, task


def _rand_email() -> str:
    tag = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"loadtest_{tag}@example.com"


class AuthenticatedUser(HttpUser):
    """Simulates a registered user performing typical API calls."""

    wait_time = between(0.5, 2)
    access_token: str = ""
    refresh_token: str = ""
    merchant_id: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_start(self):
        """Sign up a fresh user and grab tokens."""
        email = _rand_email()
        resp = self.client.post(
            "/api/v1/auth/signup",
            json={
                "email": email,
                "password": "Test1234!",
                "first_name": "Load",
                "last_name": "Tester",
            },
        )
        if resp.status_code == 201:
            data = resp.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
        else:
            # If signup fails (rate-limited), try login:
            resp = self.client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "Test1234!"},
            )
            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data["access_token"]
                self.refresh_token = data["refresh_token"]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    # ------------------------------------------------------------------
    # Auth tasks
    # ------------------------------------------------------------------

    @task(2)
    def refresh(self):
        resp = self.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": self.refresh_token},
        )
        if resp.status_code == 200:
            self.access_token = resp.json().get("access_token", self.access_token)

    @task(1)
    def validate_token(self):
        self.client.get("/api/v1/auth/validate", headers=self._headers())

    # ------------------------------------------------------------------
    # Identity tasks
    # ------------------------------------------------------------------

    @task(3)
    def get_profile(self):
        self.client.get("/api/v1/me", headers=self._headers())

    @task(1)
    def update_profile(self):
        self.client.put(
            "/api/v1/me",
            json={"phone": f"+264{random.randint(811000000, 819999999)}"},
            headers=self._headers(),
        )

    # ------------------------------------------------------------------
    # Payment tasks
    # ------------------------------------------------------------------

    @task(3)
    def list_payments(self):
        self.client.get("/api/v1/payments", headers=self._headers())

    @task(2)
    def create_and_process_payment(self):
        if not self.merchant_id:
            return  # skip when no merchant seeded
        resp = self.client.post(
            "/api/v1/payments",
            json={
                "merchant_id": self.merchant_id,
                "amount": random.randint(100, 50000),
                "currency": "NAD",
                "description": "load-test payment",
            },
            headers=self._headers(),
        )
        if resp.status_code == 201:
            pid = resp.json()["id"]
            self.client.post(
                f"/api/v1/payments/{pid}/process",
                headers=self._headers(),
            )

    # ------------------------------------------------------------------
    # Health (lightweight)
    # ------------------------------------------------------------------

    @task(5)
    def health(self):
        self.client.get("/api/v1/health")


class AdminUser(HttpUser):
    """Simulates an admin hitting stats and audit-log endpoints."""

    wait_time = between(1, 4)
    weight = 1  # far fewer admin users
    access_token: str = ""

    def on_start(self):
        """Login as the pre-seeded admin account (must exist in DB)."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@elcorp.na", "password": "Admin1234!"},
        )
        if resp.status_code == 200:
            self.access_token = resp.json()["access_token"]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    @task(3)
    def system_stats(self):
        self.client.get("/api/v1/admin/stats", headers=self._headers())

    @task(2)
    def audit_logs(self):
        self.client.get("/api/v1/admin/audit-logs?per_page=20", headers=self._headers())

    @task(1)
    def list_users(self):
        self.client.get("/api/v1/users?per_page=10", headers=self._headers())
