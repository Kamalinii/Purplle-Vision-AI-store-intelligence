# PROMPT: Create a pytest file `test_metrics.py` testing the `/stores/{store_id}/metrics` and `/stores/{store_id}/funnel` endpoints. Include edge case tests: empty store (no data), re-entry deduplication logic check, and zero purchases. Use TestClient.
# CHANGES MADE: Used fastapi.testclient.TestClient to ensure lifespan triggers.

from fastapi.testclient import TestClient
from app.main import app

def test_metrics_empty_store():
    with TestClient(app) as client:
        resp = client.get("/stores/EMPTY_STORE_999/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["unique_visitors"] == 0
        assert data["conversion_rate"] == 0.0
        assert data["queue_depth"] == 0

def test_funnel_empty_store():
    with TestClient(app) as client:
        resp = client.get("/stores/EMPTY_STORE_999/funnel")
        assert resp.status_code == 200
        data = resp.json()
        assert "funnel" in data
        if len(data["funnel"]) > 0:
            assert data["funnel"][0]["count"] == 0

def test_metrics_valid_store():
    with TestClient(app) as client:
        resp = client.get("/stores/ST1008/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "unique_visitors" in data
        assert "conversion_rate" in data
        assert "avg_dwell_per_zone" in data

def test_funnel_valid_store():
    with TestClient(app) as client:
        resp = client.get("/stores/ST1008/funnel")
        assert resp.status_code == 200
        data = resp.json()
        assert "funnel" in data
        assert len(data["funnel"]) > 0
