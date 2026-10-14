"""
MetricMind — Agentic Semantic BI Engine
FastAPI Application Entry Point
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .api.endpoints import router as api_router
from .services.data_loader import inspect_and_load_dataset

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("metricmind")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure dataset is inspected and loaded into SQLite
    logger.info("Initializing MetricMind Engine and inspecting dataset...")
    try:
        overview = inspect_and_load_dataset(force=False)
        logger.info(
            f"Dataset loaded successfully: {overview.total_orders:,} orders, "
            f"Completed Revenue: ${overview.completed_revenue:,.2f}"
        )
    except Exception as e:
        logger.error(f"Error during startup dataset ingestion: {e}", exc_info=True)
    yield
    # Shutdown logic if needed
    logger.info("MetricMind Engine shutting down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Agentic Semantic BI Engine providing governed analytics, natural language querying, and SQL transparency.",
    lifespan=lifespan
)

# CORS configuration for Next.js frontend (local dev, Vercel deployments, and custom domains)
default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
custom_origins = [
    o.strip() for o in settings.dict().get("CORS_ORIGINS", "").split(",") if o.strip()
] if hasattr(settings, "CORS_ORIGINS") else []
env_origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(set(default_origins + custom_origins + env_origins)),
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def root():
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "api_prefix": settings.API_PREFIX
    }

# Health endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": "MetricMind",
        "version": settings.VERSION,
        "database": "sqlite_ready"
    }

# Mount API endpoints
app.include_router(api_router, prefix=settings.API_PREFIX)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
