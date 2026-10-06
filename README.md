# Call Records Web Service

A simple, beginner-friendly Python FastAPI service to store and query call logs using SQLite.

---

## 📌 Features

- **`POST /call-ended`**: Accepts a JSON payload (`call_id`, `status`, `duration_secs`) and stores it into SQLite.
- **`GET /calls/{call_id}`**: Retrieves a stored call by its `call_id` or returns `404 Not Found`.
- **Validation**: Automatically validates inputs using Pydantic; missing or blank `call_id` fields return clear error messages.
- **SQLite Database**: Uses standard library `sqlite3` without extra ORM complexity.
- **Automated Tests**: Tested with `pytest` and `fastapi.testclient`.

---

## 📁 Project Structure

```text
.
├── main.py              # Main FastAPI application with SQLite database logic
├── test_main.py         # Pytest test suite testing all endpoints and edge cases
├── requirements.txt     # Python package requirements
├── pyproject.toml       # Project configuration (uv)
└── README.md            # Setup and usage documentation
```

---

## 🚀 How to Run Locally

### 1. Ensure Dependencies are Installed
If you already ran `uv add -r requirements.txt` (or `pip install -r requirements.txt`), you are ready to go.

### 2. Start the Server
Run any of the following commands:

```bash
# Using uv (recommended)
uv run uvicorn main:app --reload

# Or directly with python
uv run python main.py
```

The service will start on:
👉 **`http://127.0.0.1:8000`**

Interactive API documentation (Swagger UI) is available at:
👉 **`http://127.0.0.1:8000/docs`**

---

## 📡 API Endpoints & Examples

### 1. Record an Ended Call
- **Endpoint**: `POST /call-ended`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "call_id": "call_123",
    "status": "completed",
    "duration_secs": 45.5
  }
  ```

**Example `curl` Command:**
```bash
curl -X POST http://127.0.0.1:8000/call-ended \
  -H "Content-Type: application/json" \
  -d '{"call_id": "call_123", "status": "completed", "duration_secs": 45.5}'
```

**Success Response (`200 OK`):**
```json
{
  "call_id": "call_123",
  "status": "completed",
  "duration_secs": 45.5
}
```

---

### 2. Retrieve a Stored Call
- **Endpoint**: `GET /calls/{call_id}`

**Example `curl` Command:**
```bash
curl http://127.0.0.1:8000/calls/call_123
```

**Success Response (`200 OK`):**
```json
{
  "call_id": "call_123",
  "status": "completed",
  "duration_secs": 45.5
}
```

**Not Found Response (`404 Not Found`):**
```json
{
  "detail": "Call 'call_999' not found."
}
```

---

### 3. Missing or Invalid `call_id`
If `call_id` is omitted in the request:
```bash
curl -X POST http://127.0.0.1:8000/call-ended \
  -H "Content-Type: application/json" \
  -d '{"status": "completed", "duration_secs": 45.5}'
```

**Error Response (`422 Unprocessable Entity`):**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "call_id"],
      "msg": "Field required"
    }
  ]
}
```

If `call_id` is an empty string or spaces:
**Error Response (`400 Bad Request` or `422`):**
```json
{
  "detail": "call_id cannot be blank."
}
```

---

## 🧪 Running Tests

To run the automated test suite:

```bash
uv run pytest -v
```
