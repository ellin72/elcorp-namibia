"""HTTP client wrapper for the Elcorp API."""

from __future__ import annotations

import requests


class ElcorpClient:
    """Thin wrapper around the Elcorp REST API v1."""

    def __init__(self, base_url: str = "http://localhost:5000/api/v1", access_token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        if access_token:
            self.session.headers["Authorization"] = f"Bearer {access_token}"

    # ---- Auth ----

    def signup(self, email: str, password: str, first_name: str, last_name: str) -> dict:
        resp = self._post("/auth/signup", json={
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
        })
        self._set_token(resp.get("access_token", ""))
        return resp

    def login(self, email: str, password: str) -> dict:
        resp = self._post("/auth/login", json={"email": email, "password": password})
        self._set_token(resp.get("access_token", ""))
        return resp

    def refresh(self, refresh_token: str) -> dict:
        resp = self._post("/auth/refresh", json={"refresh_token": refresh_token})
        self._set_token(resp.get("access_token", ""))
        return resp

    # ---- Identity ----

    def get_me(self) -> dict:
        return self._get("/me")

    def update_me(self, **fields) -> dict:
        return self._put("/me", json=fields)

    def upload_kyc(self, document_type: str, file_path: str) -> dict:
        with open(file_path, "rb") as f:
            return self._post(
                "/kyc/upload",
                data={"document_type": document_type},
                files={"file": f},
                use_json=False,
            )

    def get_my_documents(self) -> list:
        return self._get("/kyc/documents")

    # ---- Payments ----

    def create_payment_token(self, instrument_type: str, last_four: str) -> dict:
        return self._post("/payments/tokens", json={
            "instrument_type": instrument_type,
            "last_four": last_four,
        })

    def create_payment(self, merchant_id: str, amount: int, currency: str = "NAD", description: str = "") -> dict:
        return self._post("/payments", json={
            "merchant_id": merchant_id,
            "amount": amount,
            "currency": currency,
            "description": description,
        })

    def process_payment(self, payment_id: str) -> dict:
        return self._post(f"/payments/{payment_id}/process")

    def get_payment(self, payment_id: str) -> dict:
        return self._get(f"/payments/{payment_id}")

    def list_payments(self, page: int = 1) -> dict:
        return self._get("/payments", params={"page": page})

    # ---- Helpers ----

    def _set_token(self, token: str) -> None:
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _get(self, path: str, **kwargs) -> dict:
        r = self.session.get(f"{self.base_url}{path}", **kwargs)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, use_json: bool = True, **kwargs) -> dict:
        r = self.session.post(f"{self.base_url}{path}", **kwargs)
        r.raise_for_status()
        return r.json()

    def _put(self, path: str, **kwargs) -> dict:
        r = self.session.put(f"{self.base_url}{path}", **kwargs)
        r.raise_for_status()
        return r.json()
