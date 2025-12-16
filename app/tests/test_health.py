"""
Tests for health and status endpoints.
"""

import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test basic health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "version" in data
    assert data["version"] == "0.1.0"


def test_readiness_check(client: TestClient):
    """Test readiness check endpoint."""
    response = client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    assert "components" in data
    assert "database" in data["components"]
    assert "api" in data["components"]


def test_status_check(client: TestClient):
    """Test detailed status endpoint."""
    response = client.get("/status")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "operational"
    assert "timestamp" in data
    assert "version" in data
    assert data["environment"] == "development"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0

    # Check components
    assert "components" in data
    assert "database" in data["components"]
    assert "api" in data["components"]
    assert "external_api" in data["components"]

    # Check metrics
    assert "metrics" in data
    assert "clients" in data["metrics"]
    assert "integrations" in data["metrics"]


def test_root_endpoint(client: TestClient):
    """Test root endpoint returns API information."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Integration Platform API"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"
    assert "endpoints" in data
    assert "health_check" in data
