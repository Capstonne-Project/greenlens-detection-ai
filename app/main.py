"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import health
from app.config import get_settings
from app.utils.logger import get_logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = get_logger(__name__)
    settings = get_settings()
    logger.info(
        "ai_service_starting",
        env=settings.app_env,
        port=settings.port,
    )
    yield
    logger.info("ai_service_stopping")


app = FastAPI(
    title="AI Service",
    description="AI microservice for pollution report analysis (SU26SE049)",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": "ai-service",
        "version": "0.1.0",
        "docs": "/docs",
    }
