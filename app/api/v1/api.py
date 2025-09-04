"""
Main API router for v1 endpoints.
"""
from fastapi import APIRouter

from app.api.v1 import analytics, utm_links, conversions, youtube_auth, youtube_analytics_endpoints, youtube_data, sync
# from app.api.v1 import auth  # Temporarily disabled for testing

api_router = APIRouter()

# Include all endpoint routers
# api_router.include_router(auth.router)  # Temporarily disabled for testing
api_router.include_router(analytics.router)
api_router.include_router(utm_links.router, tags=["utm-tracking"])
api_router.include_router(conversions.router, tags=["conversions"])
api_router.include_router(youtube_auth.router, tags=["youtube-auth"])
api_router.include_router(youtube_analytics_endpoints.router, tags=["youtube-analytics"])
api_router.include_router(youtube_data.router, tags=["youtube-data"])
api_router.include_router(sync.router, tags=["sync"])
