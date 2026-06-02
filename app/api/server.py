"""FastAPI server for the Voice Booking Agent platform.

Provides:
  - Client onboarding API (POST/GET/PUT/DELETE /api/v1/clients)
  - WebSocket voice endpoint (/ws/voice/{client_id})
  - Static frontend serving
  - Health check

Usage:
    poetry run python -m app.api.server
    # or: make api
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import auth_router
from app.api.onboard_ws import onboard_websocket_endpoint
from app.api.resources import resources_router
from app.api.routes import router
from app.api.websocket import voice_websocket_endpoint
from app.db.repositories.user_repo import UserRepository
from app.config import settings
from app.db.mongo import connect_platform, disconnect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress noisy loggers
for noisy in ["httpx", "httpcore", "openai", "urllib3"]:
    logging.getLogger(noisy).setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to platform DB on startup, disconnect on shutdown."""
    logger.info("Connecting to Platform DB...")
    db = await connect_platform(settings.mongodb_uri, settings.mongodb_database)
    await UserRepository().ensure_indexes()

    # TTL index: auto-delete checkpoints older than 24 hours
    try:
        await db["checkpoints"].create_index("created_at", expireAfterSeconds=86400)
        await db["checkpoint_writes"].create_index("created_at", expireAfterSeconds=86400)
        logger.info("Checkpoint TTL indexes ensured (24h expiry)")
    except Exception as e:
        logger.debug("Checkpoint TTL index: %s", e)

    logger.info("API server ready")
    yield
    await disconnect()
    logger.info("API server shutdown")


app = FastAPI(
    title="Voice Booking Agent — Platform API",
    description="Client onboarding, management, and real-time voice WebSocket API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST API routes
app.include_router(router)
app.include_router(auth_router)
app.include_router(resources_router)


# WebSocket voice endpoint
@app.websocket("/ws/voice/{client_id}")
async def voice_ws(websocket: WebSocket, client_id: str):
    await voice_websocket_endpoint(websocket, client_id)


# WebSocket onboarding endpoint
@app.websocket("/ws/onboard/{session_id}")
async def onboard_ws(websocket: WebSocket, session_id: str):
    await onboard_websocket_endpoint(websocket, session_id)


@app.get("/health")
async def health():
    return {"status": "ok", "database": settings.mongodb_database}


# Serve frontend static files (if built)
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(
        "app.api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
