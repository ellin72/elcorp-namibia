"""Payment gateway adapter — pluggable interface for sandbox and real providers.

Supports:
  - SandboxGateway  — instant approval for dev/test
  - PayTodayGateway — scaffold for PayToday (Namibia) integration
  - FNBGateway      — scaffold for FNB Namibia integration

Usage in payment_service:
    gateway = get_gateway()
    result = gateway.charge(amount, currency, reference, token)
"""

from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger()


@dataclass
class GatewayResult:
    success: bool
    gateway_ref: str
    status: str  # completed | failed | pending
    raw: dict  # raw response from the gateway


class BaseGateway(abc.ABC):
    """Abstract payment gateway interface."""

    @abc.abstractmethod
    def charge(
        self,
        amount: int,
        currency: str,
        reference: str,
        token: str | None = None,
        metadata: dict | None = None,
    ) -> GatewayResult:
        ...

    @abc.abstractmethod
    def refund(self, gateway_ref: str, amount: int | None = None) -> GatewayResult:
        ...

    @abc.abstractmethod
    def status(self, gateway_ref: str) -> GatewayResult:
        ...


class SandboxGateway(BaseGateway):
    """Always-approve sandbox gateway for development."""

    def charge(self, amount, currency, reference, token=None, metadata=None):
        ref = f"sb_{uuid.uuid4().hex[:12]}"
        logger.info("sandbox.charge", amount=amount, ref=ref)
        return GatewayResult(
            success=True,
            gateway_ref=ref,
            status="completed",
            raw={"provider": "sandbox", "ref": ref, "ts": datetime.now(timezone.utc).isoformat()},
        )

    def refund(self, gateway_ref, amount=None):
        ref = f"sb_refund_{uuid.uuid4().hex[:8]}"
        return GatewayResult(success=True, gateway_ref=ref, status="completed", raw={})

    def status(self, gateway_ref):
        return GatewayResult(success=True, gateway_ref=gateway_ref, status="completed", raw={})


class PayTodayGateway(BaseGateway):
    """PayToday (Namibia) gateway integration scaffold.

    Requires PAYTODAY_API_KEY and PAYTODAY_API_URL in config.
    """

    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key

    def charge(self, amount, currency, reference, token=None, metadata=None):
        import requests as http

        payload = {
            "amount": amount,
            "currency": currency,
            "reference": reference,
            "token": token,
            "metadata": metadata or {},
        }
        try:
            resp = http.post(
                f"{self.api_url}/v1/charges",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            data = resp.json()
            return GatewayResult(
                success=resp.status_code == 200,
                gateway_ref=data.get("id", ""),
                status=data.get("status", "failed"),
                raw=data,
            )
        except Exception as exc:
            logger.error("paytoday.charge_failed", error=str(exc))
            return GatewayResult(success=False, gateway_ref="", status="failed", raw={"error": str(exc)})

    def refund(self, gateway_ref, amount=None):
        import requests as http

        try:
            resp = http.post(
                f"{self.api_url}/v1/refunds",
                json={"charge_id": gateway_ref, "amount": amount},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30,
            )
            data = resp.json()
            return GatewayResult(
                success=resp.status_code == 200,
                gateway_ref=data.get("id", ""),
                status=data.get("status", "failed"),
                raw=data,
            )
        except Exception as exc:
            return GatewayResult(success=False, gateway_ref="", status="failed", raw={"error": str(exc)})

    def status(self, gateway_ref):
        import requests as http

        try:
            resp = http.get(
                f"{self.api_url}/v1/charges/{gateway_ref}",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=15,
            )
            data = resp.json()
            return GatewayResult(
                success=True,
                gateway_ref=gateway_ref,
                status=data.get("status", "unknown"),
                raw=data,
            )
        except Exception as exc:
            return GatewayResult(success=False, gateway_ref=gateway_ref, status="unknown", raw={"error": str(exc)})


class FNBGateway(BaseGateway):
    """FNB Namibia gateway integration scaffold."""

    def __init__(self, api_url: str, api_key: str, merchant_code: str):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.merchant_code = merchant_code

    def charge(self, amount, currency, reference, token=None, metadata=None):
        import requests as http

        try:
            resp = http.post(
                f"{self.api_url}/payments",
                json={
                    "merchantCode": self.merchant_code,
                    "amount": amount,
                    "currency": currency,
                    "reference": reference,
                },
                headers={"X-API-Key": self.api_key},
                timeout=30,
            )
            data = resp.json()
            return GatewayResult(
                success=resp.status_code in (200, 201),
                gateway_ref=data.get("transactionId", ""),
                status=data.get("status", "failed"),
                raw=data,
            )
        except Exception as exc:
            logger.error("fnb.charge_failed", error=str(exc))
            return GatewayResult(success=False, gateway_ref="", status="failed", raw={"error": str(exc)})

    def refund(self, gateway_ref, amount=None):
        # FNB refund scaffold
        return GatewayResult(success=False, gateway_ref="", status="not_implemented", raw={})

    def status(self, gateway_ref):
        # FNB status scaffold
        return GatewayResult(success=False, gateway_ref=gateway_ref, status="not_implemented", raw={})


_gateway_instance: BaseGateway | None = None


def get_gateway() -> BaseGateway:
    """Return the configured gateway (singleton per process)."""
    global _gateway_instance
    if _gateway_instance is not None:
        return _gateway_instance

    from flask import current_app

    provider = current_app.config.get("PAYMENT_GATEWAY_PROVIDER", "sandbox")

    if provider == "paytoday":
        _gateway_instance = PayTodayGateway(
            api_url=current_app.config["PAYTODAY_API_URL"],
            api_key=current_app.config["PAYTODAY_API_KEY"],
        )
    elif provider == "fnb":
        _gateway_instance = FNBGateway(
            api_url=current_app.config["FNB_API_URL"],
            api_key=current_app.config["FNB_API_KEY"],
            merchant_code=current_app.config["FNB_MERCHANT_CODE"],
        )
    else:
        _gateway_instance = SandboxGateway()

    logger.info("gateway.initialized", provider=provider)
    return _gateway_instance
