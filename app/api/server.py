"""FastAPI server for the Voice Booking Agent platform.

Provides:
  - Client onboarding API (POST/GET/PUT/DELETE /api/v1/clients)
  - Health check

Usage:
    poetry run python -m app.api.server
    # or: make api
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.db.mongo import connect_platform, disconnect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to platform DB on startup, disconnect on shutdown."""
    logger.info("Connecting to Platform DB...")
    await connect_platform(settings.mongodb_uri, settings.mongodb_database)
    logger.info("API server ready")
    yield
    await disconnect()
    logger.info("API server shutdown")


app = FastAPI(
    title="Voice Booking Agent — Platform API",
    description="Client onboarding and management API",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "database": settings.mongodb_database}


if __name__ == "__main__":
    uvicorn.run(
        "app.api.server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
