"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1 import classify, health
from app.config import get_settings
from app.utils.logger import get_logger, setup_logging

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEMO_STATIC = _REPO_ROOT / "static" / "demo"


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
app.include_router(classify.router, prefix="/api/v1")

if _DEMO_STATIC.is_dir():
    app.mount(
        "/demo",
        StaticFiles(directory=str(_DEMO_STATIC), html=False),
        name="demo",
    )


@app.get("/")
async def root():
    return {
        "service": "ai-service",
        "version": "0.1.0",
        "docs": "/docs",
        "demo_capture_classify": "/demo/demo_capture_classify.html",
    }
