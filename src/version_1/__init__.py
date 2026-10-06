# pyrefly: ignore [missing-import]
import uvicorn
from main import app

def main() -> None:
    """Entry point to run the Call Records Service."""
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
