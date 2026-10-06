import sqlite3
import os
import tempfile
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

# Use a temporary database for test isolation
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()

os.environ["CALLS_DB_PATH"] = temp_db_path

# pyrefly: ignore [missing-import]
from main import app, init_db

# Ensure table exists in the temporary test database
init_db(temp_db_path)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Clean the calls table before each test."""
    import sqlite3
    with sqlite3.connect(temp_db_path) as conn:
        conn.execute("DELETE FROM calls")
    yield


def test_root_endpoint():
    """Verify that the health check endpoint returns 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Call Records Service" in response.json()["message"]


def test_record_call_success():
    """Test successful recording of a call via POST /call-ended."""
    payload = {
        "call_id": "call_abc_123",
        "status": "completed",
        "duration_secs": 45.5,
    }
    response = client.post("/call-ended", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["call_id"] == "call_abc_123"
    assert data["status"] == "completed"
    assert data["duration_secs"] == 45.5


def test_get_call_success():
    """Test retrieving an existing call record via GET /calls/{call_id}."""
    payload = {
        "call_id": "call_xyz_789",
        "status": "in-progress",
        "duration_secs": 120.0,
    }
    # First save the call
    post_res = client.post("/call-ended", json=payload)
    assert post_res.status_code == 200

    # Retrieve the call
    get_res = client.get("/calls/call_xyz_789")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["call_id"] == "call_xyz_789"
    assert data["status"] == "in-progress"
    assert data["duration_secs"] == 120.0


def test_get_call_not_found():
    """Test that querying a non-existent call_id returns 404 Not Found."""
    response = client.get("/calls/non_existent_id")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_missing_call_id_returns_clear_error():
    """Test that omitting call_id returns a clear validation error."""
    payload = {
        "status": "completed",
        "duration_secs": 30.0,
    }
    response = client.post("/call-ended", json=payload)
    # FastAPI returns 422 for missing required Pydantic fields
    assert response.status_code in (400, 422)
    # Ensure error detail explicitly highlights call_id
    detail_str = str(response.json())
    assert "call_id" in detail_str


def test_empty_call_id_returns_clear_error():
    """Test that passing an empty string as call_id returns an error."""
    payload = {
        "call_id": "   ",
        "status": "completed",
        "duration_secs": 30.0,
    }
    response = client.post("/call-ended", json=payload)
    assert response.status_code in (400, 422)
    detail_str = str(response.json())
    assert "call_id" in detail_str


def test_missing_status_returns_clear_error():
    """Test that omitting status returns a validation error."""
    payload = {
        "call_id": "call_123",
        "duration_secs": 30.0,
    }
    response = client.post("/call-ended", json=payload)
    assert response.status_code in (400, 422)


def test_negative_duration_returns_clear_error():
    """Test that negative duration_secs returns a validation error."""
    payload = {
        "call_id": "call_123",
        "status": "completed",
        "duration_secs": -5.0,
    }
    response = client.post("/call-ended", json=payload)
    assert response.status_code in (400, 422)


def test_duplicate_call_is_not_stored_twice():
    """Test that sending the same call twice creates only one record."""

    payload = {
        "call_id": "call_repeat_1",
        "status": "completed",
        "duration_secs": 42.0,
    }

    first = client.post("/call-ended", json=payload)
    second = client.post("/call-ended", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200

    with sqlite3.connect(temp_db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM calls WHERE call_id = ?",
            ("call_repeat_1",)
        ).fetchone()

    assert row[0] == 1