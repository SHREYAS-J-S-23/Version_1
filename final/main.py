import os
import sqlite3
from contextlib import asynccontextmanager

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


# SQLite database path
DB_PATH = os.getenv("CALLS_DB_PATH", "calls.db")


def get_db_connection() -> sqlite3.Connection:
    """Create a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Create the calls table if it does not already exist."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calls (
                call_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                duration_secs INTEGER NOT NULL
            )
            """
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database when the application starts."""
    init_db()
    yield


app = FastAPI(
    title="Call Records Service",
    description="A simple idempotent webhook service for call records.",
    version="2.0.0",
    lifespan=lifespan,
)


class CallEndedRequest(BaseModel):
    call_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the call",
    )
    status: str = Field(
        ...,
        min_length=1,
        description="Status of the call",
    )
    duration_secs: int = Field(
        ...,
        ge=0,
        description="Call duration in seconds",
    )


class CallResponse(BaseModel):
    call_id: str
    status: str
    duration_secs: int


@app.get("/", summary="Health check")
def root():
    return {
        "message": "Call Records Service is running. Visit /docs for API documentation."
    }


@app.post(
    "/call-ended",
    response_model=CallResponse,
    status_code=status.HTTP_200_OK,
    summary="Record an ended call",
)
def record_call_ended(payload: CallEndedRequest):

    call_id = payload.call_id.strip()
    call_status = payload.status.strip()

    if not call_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="call_id cannot be blank.",
        )

    if not call_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status cannot be blank.",
        )

    with get_db_connection() as conn:

        # Store the call only if this call_id does not already exist.
        # A duplicate request is intentionally ignored.
        conn.execute(
            """
            INSERT INTO calls (call_id, status, duration_secs)
            VALUES (?, ?, ?)
            ON CONFLICT(call_id) DO NOTHING
            """,
            (
                call_id,
                call_status,
                payload.duration_secs,
            ),
        )

        # Return the stored record, whether this was the first
        # request or a duplicate request.
        row = conn.execute(
            """
            SELECT call_id, status, duration_secs
            FROM calls
            WHERE call_id = ?
            """,
            (call_id,),
        ).fetchone()

    return CallResponse(
        call_id=row["call_id"],
        status=row["status"],
        duration_secs=row["duration_secs"],
    )


@app.get(
    "/calls/{call_id}",
    response_model=CallResponse,
    summary="Retrieve a call by call_id",
)
def get_call(call_id: str):

    cleaned_id = call_id.strip()

    if not cleaned_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="call_id cannot be blank.",
        )

    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT call_id, status, duration_secs
            FROM calls
            WHERE call_id = ?
            """,
            (cleaned_id,),
        ).fetchone()

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

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )