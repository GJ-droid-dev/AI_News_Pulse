import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os

# Set a dummy DB URL so DigestStore doesn't raise ValueError during initialization
os.environ["DATABASE_URL"] = "postgres://dummy:dummy@localhost:5432/dummy"

from src.delivery.api import app

client = TestClient(app)

@patch("src.delivery.api.get_digest_by_date")
def test_get_today_digest_success(mock_get_digest):
    """Test retrieving today's digest when it exists."""
    mock_get_digest.return_value = {
        "date": "2026-07-20",
        "highlight_json": {"executive_summary": "Test Summary"},
        "markdown_content": "# Test",
        "generated_at": "2026-07-20T12:00:00Z"
    }
    
    response = client.get("/v1/digest/today")
    assert response.status_code == 200
    assert response.json()["date"] == "2026-07-20"
    
@patch("src.delivery.api.get_digest_by_date")
def test_get_today_digest_not_found(mock_get_digest):
    """Test retrieving today's digest when it hasn't been generated yet (404)."""
    mock_get_digest.return_value = None
    response = client.get("/v1/digest/today")
    assert response.status_code == 404

@patch("src.delivery.api.get_digest_by_date")
def test_get_digest_by_date(mock_get_digest):
    """Test retrieving a specific historical date."""
    mock_get_digest.return_value = {
        "date": "2026-07-15",
        "markdown_content": "# Old Digest"
    }
    response = client.get("/v1/digest/2026-07-15")
    assert response.status_code == 200
    assert response.json()["date"] == "2026-07-15"

@patch("src.delivery.api.store")
def test_get_archive(mock_store):
    """Test retrieving the paginated list of digests."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # Mock the DB context managers
    mock_store.get_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    mock_cursor.fetchall.return_value = [
        {"date": "2026-07-20", "highlight_json": {}, "generated_at": "2026-07-20"}
    ]
    
    response = client.get("/v1/digest/archive/list")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["date"] == "2026-07-20"

@patch("src.delivery.api.store")
def test_health_check(mock_store):
    """Test the health endpoint database connectivity check."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_store.get_connection.return_value.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"
    assert response.json()["status"] == "ok"
