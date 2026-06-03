# PROMPT: Generate a test case for `/stores/{store_id}/heatmap` using TestClient.
# CHANGES MADE: Added check for data_confidence field as requested in the instructions.

from fastapi.testclient import TestClient
from app.main import app

def test_heatmap_valid_store():
    with TestClient(app) as client:
        resp = client.get("/stores/ST1008/heatmap")
        assert resp.status_code == 200
        data = resp.json()
        assert "zones" in data
        assert "data_confidence" in data

def test_heatmap_empty_store():
    with TestClient(app) as client:
        resp = client.get("/stores/EMPTY_STORE/heatmap")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data_confidence"] == False
