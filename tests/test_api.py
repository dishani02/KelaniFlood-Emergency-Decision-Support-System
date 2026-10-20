from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)


def test_alert_endpoint_inside_zone():
    # Point clearly inside the KLN-DS-01 zone (79.89 to 79.92, 6.91 to 6.935)
    r = client.post("/api/alert", json={"lat": 6.92, "lon": 79.91})
    assert r.status_code == 200 and r.json()["severity"] == "CRITICAL"


def test_alert_rejects_bad_coordinates():
    assert client.post("/api/alert", json={"lat": 999, "lon": 79.9}).status_code == 422


def test_feed_must_contain_zones():
    assert client.post("/api/feed", json={"foo": 1}).status_code == 422