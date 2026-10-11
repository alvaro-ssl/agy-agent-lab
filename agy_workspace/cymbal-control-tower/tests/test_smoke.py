"""Smoke tests run by the release pipeline before every Control Tower deploy."""

from fastapi.testclient import TestClient

import database
from app import app

database.init_db()
client = TestClient(app)


def test_dashboard_is_served():
    assert client.get("/").status_code == 200


def test_overview_endpoint_responds():
    response = client.get("/api/overview")
    assert response.status_code == 200
    assert len(response.json()["services"]) == 12


def test_feeds_respond():
    for path in ("/api/incidents", "/api/deploys", "/api/approvals"):
        assert client.get(path).status_code == 200


def test_timeseries_responds():
    response = client.get("/api/services/checkout-api/timeseries")
    assert response.status_code == 200
    assert len(response.json()["points"]) == database.BUCKETS
