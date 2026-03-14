"""Tests for health endpoints."""


class TestHealth:
    def test_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "healthy"

    def test_readiness(self, client):
        resp = client.get("/api/v1/health/ready")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ready"
        assert data["checks"]["database"]["status"] == "ok"
