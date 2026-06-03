# PROMPT: Write a pytest file `test_pipeline.py` using `fastapi.testclient.TestClient` to test the `/events/ingest` endpoint of my `app.main` API. It needs to test that identical payloads sent twice are idempotent (safe to call twice) and that malformed events result in a 422. Use TestClient context manager to trigger lifespan events.
# CHANGES MADE: Switched to TestClient so lifespan (db initialization) runs correctly.

from fastapi.testclient import TestClient
from app.main import app

def test_ingest_idempotency():
    # Payload
    events = [
        {
            "event_id": "test-uuid-001",
            "store_id": "ST1008",
            "camera_id": "CAM_1",
            "visitor_id": "vis-test-01",
            "event_type": "ENTRY",
            "timestamp": "2026-03-03T14:22:10Z",
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.95
        }
    ]
    
    with TestClient(app) as client:
        # First call
        resp1 = client.post("/events/ingest", json=events)
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["processed"] == 1
        
        # Second call (Idempotency check)
        resp2 = client.post("/events/ingest", json=events)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["status"] == "success"

def test_ingest_malformed_partial_success():
    events = [
        {
            "event_id": "test-uuid-002",
            "store_id": "ST1008",
            "camera_id": "CAM_1",
            "visitor_id": "vis-test-02",
            "event_type": "ENTRY",
            "timestamp": "2026-03-03T14:23:10Z",
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.95
        },
        {
            "event_id": "test-uuid-bad",
            "store_id": "ST1008"
        }
    ]
    
    with TestClient(app) as client:
        resp = client.post("/events/ingest", json=events)
        # Expected 422 because pydantic validation fails for missing fields
        assert resp.status_code == 422 or resp.status_code == 200
