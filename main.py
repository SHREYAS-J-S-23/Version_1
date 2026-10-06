import os
import sqlite3
from contextlib import asynccontextmanager

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

# SQLite database file name (can be overridden via environment variable)
DB_PATH = os.getenv("CALLS_DB_PATH", "calls.db")


def get_db_connection() -> sqlite3.Connection:
    """Create and return a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Initialize the SQLite database schema if the table does not exist."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calls (
                call_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                duration_secs REAL NOT NULL
            )
            """
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to initialize database on application startup."""
    init_db()
    yield


# Initialize FastAPI app
app = FastAPI(
    title="Call Records Service",
    description="A simple, beginner-friendly FastAPI service for recording and retrieving call logs.",
    version="1.0.0",
    lifespan=lifespan,
)

# Ensure database table is created when module is loaded
init_db()


# ---------------------------------------------------------
# Request & Response Models (Pydantic)
# ---------------------------------------------------------
class CallEndedRequest(BaseModel):
    call_id: str = Field(..., min_length=1, description="Unique identifier for the call")
    status: str = Field(..., min_length=1, description="Status of the call, e.g., 'completed', 'failed'")
    duration_secs: float = Field(..., ge=0, description="Call duration in seconds (must be >= 0)")


class CallResponse(BaseModel):
    call_id: str
    status: str
    duration_secs: float


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------
@app.get("/", summary="Health check")
def root():
    """Simple root endpoint to confirm the service is running."""
    return {"message": "Call Records Service is running. Visit /docs for API documentation."}


@app.post(
    "/call-ended",
    response_model=CallResponse,
    status_code=status.HTTP_200_OK,
    summary="Record an ended call",
)
def record_call_ended(payload: CallEndedRequest):
    """
    Accepts JSON containing call_id, status, and duration_secs.
    Stores the call record in SQLite.
    If call_id is missing or blank, returns a clear error.
    """
    call_id = payload.call_id.strip()
    status_val = payload.status.strip()

    if not call_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="call_id cannot be blank.",
        )
    if not status_val:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status cannot be blank.",
        )

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO calls (call_id, status, duration_secs)
            VALUES (?, ?, ?)
            ON CONFLICT(call_id) DO UPDATE SET
                status = excluded.status,
                duration_secs = excluded.duration_secs
            """,
            (call_id, status_val, payload.duration_secs),
        )

    return CallResponse(
        call_id=call_id,
        status=status_val,
        duration_secs=payload.duration_secs,
    )


@app.get(
    "/calls/{call_id}",
    response_model=CallResponse,
    summary="Retrieve a call by call_id",
)
def get_call(call_id: str):
    """
    Returns the stored call matching the given call_id.
    Returns HTTP 404 Not Found if the call is not found.
    """
    cleaned_id = call_id.strip()
    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="call_id path parameter cannot be blank.",
        )

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT call_id, status, duration_secs FROM calls WHERE call_id = ?",
            (cleaned_id,),
        )
        row = cursor.fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call '{cleaned_id}' not found.",
        )

    return CallResponse(
        call_id=row["call_id"],
        status=row["status"],
        duration_secs=row["duration_secs"],
    )


if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
