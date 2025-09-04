"""
Main FastAPI application entry point for YouTube Analytics API.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from loguru import logger

from app.core.config import settings
from app.core.exceptions import (
    YouTubeAPIError, ScrapeCreatorsAPIError, AuthenticationError,
    DataNotFoundError, ValidationError,
    youtube_api_exception_handler, scrapecreators_api_exception_handler,
    authentication_exception_handler, data_not_found_exception_handler,
    validation_exception_handler, general_exception_handler
)
from app.core.database import create_tables

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add custom exception handlers
app.add_exception_handler(YouTubeAPIError, youtube_api_exception_handler)
app.add_exception_handler(ScrapeCreatorsAPIError, scrapecreators_api_exception_handler)
app.add_exception_handler(AuthenticationError, authentication_exception_handler)
app.add_exception_handler(DataNotFoundError, data_not_found_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Configure CORS
print(f"DEBUG: CORS origins: {settings.cors_origins}")
print(f"DEBUG: Environment: {settings.ENVIRONMENT}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "YouTube Analytics API",
        "version": settings.VERSION,
        "docs": "/docs",
        "redoc": "/redoc",
        "api_v1": settings.API_V1_STR
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "YouTube Analytics API", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment verification."""
    return {"status": "healthy", "message": "API is running"}


# Include API routers
from app.api.v1.api import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)


# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables and perform startup tasks."""
    logger.info("Starting up YouTube Analytics API...")
    create_tables()
    logger.info("Database tables created/verified")

    # Start the daily sync scheduler
    try:
        from app.services.scheduler_service import start_scheduler
        await start_scheduler()
        logger.info("Daily sync scheduler started")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup tasks on shutdown."""
    logger.info("Shutting down YouTube Analytics API...")

    # Stop the daily sync scheduler
    try:
        from app.services.scheduler_service import stop_scheduler
        await stop_scheduler()
        logger.info("Daily sync scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

    logger.info("Shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
