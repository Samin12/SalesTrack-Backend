"""
Core configuration settings for the YouTube Analytics API.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import validator
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "YouTube Analytics API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "YouTube Analytics Tracking System API"
    BASE_URL: str = "http://localhost:8000"
    
    # Database
    DATABASE_URL: str = "sqlite:///./youtube_analytics.db"

    # Supabase Configuration
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    
    # YouTube API Configuration
    YOUTUBE_API_KEY: str
    YOUTUBE_CHANNEL_ID: str
    YOUTUBE_CHANNEL_HANDLE: str = "@SaminYasar_"

    # YouTube OAuth Configuration (for Analytics API)
    YOUTUBE_OAUTH_CONFIG: Optional[str] = None  # JSON string of OAuth config
    
    # ScrapeCreators API Configuration
    SCRAPECREATORS_API_KEY: str = "wHAmZcysPNY6yDhX0impv2Lv5dg1"
    SCRAPECREATORS_BASE_URL: str = "https://api.scrapecreators.com"

    # Google Analytics 4 Configuration (keeping for migration period)
    GA4_PROPERTY_ID: Optional[str] = None
    GA4_MEASUREMENT_ID: Optional[str] = None
    GA4_API_SECRET: Optional[str] = None
    GA4_SERVICE_ACCOUNT_PATH: Optional[str] = None

    # PostHog Analytics Configuration
    POSTHOG_API_KEY: Optional[str] = None
    POSTHOG_HOST: str = "https://us.posthog.com"
    POSTHOG_PROJECT_ID: Optional[str] = None
    
    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001", "http://localhost:3002", "http://localhost:8080"]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Production Configuration
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins based on environment."""
        if self.is_production:
            # In production, get from environment variable or use defaults
            cors_env = os.getenv("CORS_ORIGINS", "")
            if cors_env:
                return [origin.strip() for origin in cors_env.split(",")]
            return ["*"]  # Allow all origins in production (configure as needed)
        return self.BACKEND_CORS_ORIGINS
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # YouTube OAuth Scopes
    YOUTUBE_SCOPES: List[str] = [
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
        "https://www.googleapis.com/auth/youtube.channel-memberships.creator"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()


# Database configuration
def get_database_url() -> str:
    """Get the database URL for SQLAlchemy."""
    return settings.DATABASE_URL


# Google OAuth configuration
def get_google_oauth_config() -> dict:
    """Get Google OAuth configuration."""
    return {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scopes": settings.YOUTUBE_SCOPES
    }


# YouTube API configuration
def get_youtube_config() -> dict:
    """Get YouTube API configuration."""
    return {
        "api_key": settings.YOUTUBE_API_KEY,
        "channel_id": settings.YOUTUBE_CHANNEL_ID,
        "channel_handle": settings.YOUTUBE_CHANNEL_HANDLE
    }


# ScrapeCreators API configuration
def get_scrapecreators_config() -> dict:
    """Get ScrapeCreators API configuration."""
    return {
        "api_key": settings.SCRAPECREATORS_API_KEY,
        "base_url": settings.SCRAPECREATORS_BASE_URL
    }


# Google Analytics 4 configuration
def get_ga4_config() -> dict:
    """Get Google Analytics 4 configuration."""
    return {
        "property_id": settings.GA4_PROPERTY_ID,
        "measurement_id": settings.GA4_MEASUREMENT_ID,
        "api_secret": settings.GA4_API_SECRET,
        "service_account_path": settings.GA4_SERVICE_ACCOUNT_PATH
    }


# PostHog Analytics configuration
def get_posthog_config() -> dict:
    """Get PostHog Analytics configuration."""
    return {
        "api_key": settings.POSTHOG_API_KEY,
        "host": settings.POSTHOG_HOST,
        "project_id": settings.POSTHOG_PROJECT_ID
    }


# Supabase configuration
def get_supabase_config() -> dict:
    """Get Supabase configuration."""
    return {
        "url": settings.SUPABASE_URL,
        "key": settings.SUPABASE_KEY,
        "service_role_key": settings.SUPABASE_SERVICE_ROLE_KEY
    }
