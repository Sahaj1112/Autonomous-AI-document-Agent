import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    """Verifies that the /health API endpoint is live and returning correct values."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_download_document_invalid_filename() -> None:
    """Verifies that download route rejects path traversal attempts."""
    response = client.get("/documents/..%5Csecret.docx")
    assert response.status_code == 400
    assert "Invalid filename" in response.json()["detail"]


def test_download_document_not_found() -> None:
    """Verifies that download route returns 404 for non-existent files."""
    response = client.get("/documents/non_existent_document_123.docx")
    assert response.status_code == 404
    assert "document file does not exist" in response.json()["detail"]


def test_agent_route_validation() -> None:
    """Verifies that POST /agent enforces validation constraints (e.g. short request)."""
    # Request body must contain "request" field
    response = client.post("/agent", json={})
    assert response.status_code == 422

    # Request string is too short (less than 10 characters)
    response = client.post("/agent", json={"request": "Short"})
    assert response.status_code == 422
