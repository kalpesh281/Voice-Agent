"""One-file backend starter.

Usage:
    python3 server.py
    # or: poetry run python server.py
"""

from app.api.server import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
