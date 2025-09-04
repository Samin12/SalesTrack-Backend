"""
Custom exception classes and error handlers.
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger
from typing import Any, Dict, Optional


class YouTubeAPIError(Exception):
    """Exception raised for YouTube API errors."""
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ScrapeCreatorsAPIError(Exception):
    """Exception raised for ScrapeCreators API errors."""
    
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(Exception):
    """Exception raised for authentication errors."""
    
    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)


class DataNotFoundError(Exception):
    """Exception raised when requested data is not found."""
    
    def __init__(self, message: str = "Data not found"):
        self.message = message
        super().__init__(self.message)


class ValidationError(Exception):
    """Exception raised for data validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


# Exception handlers
async def youtube_api_exception_handler(request: Request, exc: YouTubeAPIError):
    """Handle YouTube API exceptions."""
    logger.error(f"YouTube API error: {exc.message} - Details: {exc.details}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message,
            "error_code": "YOUTUBE_API_ERROR",
            "details": exc.details
        }
    )


async def scrapecreators_api_exception_handler(request: Request, exc: ScrapeCreatorsAPIError):
    """Handle ScrapeCreators API exceptions."""
    logger.error(f"ScrapeCreators API error: {exc.message} - Details: {exc.details}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message,
            "error_code": "SCRAPECREATORS_API_ERROR",
            "details": exc.details
        }
    )


async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication exceptions."""
    logger.warning(f"Authentication error: {exc.message}")
    return JSONResponse(
        status_code=401,
        content={
            "status": "error",
            "message": exc.message,
            "error_code": "AUTHENTICATION_ERROR"
        }
    )


async def data_not_found_exception_handler(request: Request, exc: DataNotFoundError):
    """Handle data not found exceptions."""
    logger.info(f"Data not found: {exc.message}")
    return JSONResponse(
        status_code=404,
        content={
            "status": "error",
            "message": exc.message,
            "error_code": "DATA_NOT_FOUND"
        }
    )


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle validation exceptions."""
    logger.warning(f"Validation error: {exc.message} - Field: {exc.field}")
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": exc.message,
            "error_code": "VALIDATION_ERROR",
            "field": exc.field
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An unexpected error occurred",
            "error_code": "INTERNAL_SERVER_ERROR"
        }
    )
