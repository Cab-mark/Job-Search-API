"""
Job Search API - Main Application Entry Point

This FastAPI application provides a RESTful API for searching job listings
stored in OpenSearch. It interfaces with the Next.js frontend application
(nextjs_govuk_experiment) using a shared TypeScript/Pydantic interface.

Startup Events:
- Creates OpenSearch client
- Ensures the jobs index exists with proper mapping

Endpoints:
- GET /health - Health check endpoint
- GET /jobs - Search jobs with query and filters
- GET /jobs/{id} - Get a specific job by ID
- POST /jobs - Create a new job (local development)
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.models import HealthResponse
from app.opensearch_client import (
    ensure_index_exists,
    check_opensearch_connection,
    close_client
)
from app.routers import search

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events.
    
    Startup:
    - Creates OpenSearch client connection
    - Ensures the jobs index exists with proper mapping
    
    Shutdown:
    - Closes the OpenSearch client connection
    """
    # Startup
    logger.info("Starting Job Search API...")
    settings = get_settings()
    
    try:
        # Check OpenSearch connection and create index
        if check_opensearch_connection():
            logger.info("OpenSearch connection established")
            ensure_index_exists()
            logger.info(f"Jobs index '{settings.opensearch_index}' ready")
        else:
            logger.warning("OpenSearch not available at startup - will retry on first request")
    except Exception as e:
        logger.error(f"Failed to initialize OpenSearch: {e}")
        # Don't fail startup - allow the app to start and retry later
    
    logger.info("Job Search API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Job Search API...")
    close_client()
    logger.info("Job Search API shutdown complete")


# Get settings for API metadata
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS for frontend integration
# In production, restrict origins to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(search.router)


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns the health status of the API and its connection to OpenSearch.
    Use this endpoint for container health checks and monitoring.
    
    Returns:
        HealthResponse: Health status including OpenSearch connectivity
    """
    opensearch_connected = check_opensearch_connection()
    
    return HealthResponse(
        status="healthy" if opensearch_connected else "degraded",
        opensearch_connected=opensearch_connected,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint returning API information.
    
    Returns:
        dict: API name and version
    """
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs"
    }
