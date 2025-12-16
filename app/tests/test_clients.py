"""
Tests for client endpoints.
"""

from fastapi.testclient import TestClient


def test_create_client(client: TestClient, sample_client_data):
    """Test creating a new client."""
    response = client.post("/api/v1/clients", json=sample_client_data)

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == sample_client_data["name"]
    assert data["description"] == sample_client_data["description"]
    assert data["external_api_url"] == sample_client_data["external_api_url"]
    assert data["is_active"] == sample_client_data["is_active"]
    assert "id" in data
    assert "api_key" in data
    assert data["api_key"].startswith("pk_")
    assert data["has_credentials"] is True
    assert "created_at" in data
    assert "updated_at" in data


def test_create_client_without_credentials(client: TestClient):
    """Test creating a client without credentials."""
    client_data = {
        "name": "Client Without Creds",
        "description": "Test client",
        "is_active": True,
    }

    response = client.post("/api/v1/clients", json=client_data)

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == client_data["name"]
    assert data["has_credentials"] is False


def test_list_clients_empty(client: TestClient):
    """Test listing clients when database is empty."""
    response = client.get("/api/v1/clients")

    assert response.status_code == 200
    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 50
    assert data["pages"] == 0


def test_list_clients(client: TestClient, sample_client_data):
    """Test listing clients."""
    # Create a client first
    client.post("/api/v1/clients", json=sample_client_data)

    response = client.get("/api/v1/clients")

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 1
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["pages"] == 1


def test_list_clients_pagination(client: TestClient, sample_client_data):
    """Test client list pagination."""
    # Create multiple clients
    for i in range(3):
        client_data = sample_client_data.copy()
        client_data["name"] = f"Client {i}"
        client.post("/api/v1/clients", json=client_data)

    # Get first page with page_size=2
    response = client.get("/api/v1/clients?page=1&page_size=2")

    assert response.status_code == 200
    data = response.json()

    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["pages"] == 2


def test_get_client(client: TestClient, sample_client_data):
    """Test getting a specific client."""
    # Create a client
    create_response = client.post("/api/v1/clients", json=sample_client_data)
    client_id = create_response.json()["id"]

    # Get the client
    response = client.get(f"/api/v1/clients/{client_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == client_id
    assert data["name"] == sample_client_data["name"]
    assert data["has_credentials"] is True


def test_get_client_not_found(client: TestClient):
    """Test getting a non-existent client."""
    response = client.get("/api/v1/clients/9999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_client_credentials(client: TestClient, sample_client_data):
    """Test getting client with decrypted credentials."""
    # Create a client
    create_response = client.post("/api/v1/clients", json=sample_client_data)
    client_id = create_response.json()["id"]

    # Get credentials
    response = client.get(f"/api/v1/clients/{client_id}/credentials")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == client_id
    assert data["credentials"] is not None
    assert data["credentials"]["api_key"] == sample_client_data["credentials"]["api_key"]
    assert data["credentials"]["api_secret"] == sample_client_data["credentials"]["api_secret"]


def test_update_client(client: TestClient, sample_client_data):
    """Test updating a client."""
    # Create a client
    create_response = client.post("/api/v1/clients", json=sample_client_data)
    client_id = create_response.json()["id"]

    # Update the client
    update_data = {"name": "Updated Client Name", "is_active": False}
    response = client.put(f"/api/v1/clients/{client_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == client_id
    assert data["name"] == update_data["name"]
    assert data["is_active"] == update_data["is_active"]


def test_update_client_not_found(client: TestClient):
    """Test updating a non-existent client."""
    update_data = {"name": "Updated Name"}
    response = client.put("/api/v1/clients/9999", json=update_data)

    assert response.status_code == 404


def test_delete_client(client: TestClient, sample_client_data):
    """Test deleting a client."""
    # Create a client
    create_response = client.post("/api/v1/clients", json=sample_client_data)
    client_id = create_response.json()["id"]

    # Delete the client
    response = client.delete(f"/api/v1/clients/{client_id}")

    assert response.status_code == 204

    # Verify client is deleted
    get_response = client.get(f"/api/v1/clients/{client_id}")
    assert get_response.status_code == 404


def test_delete_client_not_found(client: TestClient):
    """Test deleting a non-existent client."""
    response = client.delete("/api/v1/clients/9999")

    assert response.status_code == 404


def test_client_filter_by_active_status(client: TestClient, sample_client_data):
    """Test filtering clients by active status."""
    # Create active client
    active_data = sample_client_data.copy()
    active_data["name"] = "Active Client"
    active_data["is_active"] = True
    client.post("/api/v1/clients", json=active_data)

    # Create inactive client
    inactive_data = sample_client_data.copy()
    inactive_data["name"] = "Inactive Client"
    inactive_data["is_active"] = False
    client.post("/api/v1/clients", json=inactive_data)

    # Filter for active clients only
    response = client.get("/api/v1/clients?is_active=true")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["is_active"] is True

    # Filter for inactive clients only
    response = client.get("/api/v1/clients?is_active=false")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["is_active"] is False
