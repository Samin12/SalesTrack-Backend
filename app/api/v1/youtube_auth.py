"""
YouTube OAuth authentication endpoints for Analytics API access.
"""
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.services.youtube_analytics import YouTubeAnalyticsService
from app.models.oauth_token import YouTubeOAuthToken
from app.core.config import settings


router = APIRouter(prefix="/youtube-auth", tags=["YouTube Authentication"])


@router.get("/authorize")
async def start_youtube_authorization(request: Request, db: Session = Depends(get_db)):
    """Start the YouTube OAuth authorization flow."""
    try:
        youtube_analytics = YouTubeAnalyticsService(db)
        
        # Build redirect URI
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/api/v1/youtube-auth/callback"
        
        # Get authorization URL
        auth_url = youtube_analytics.get_authorization_url(redirect_uri)
        
        logger.info(f"Starting YouTube OAuth flow, redirecting to: {auth_url}")
        
        return {
            "status": "success",
            "authorization_url": auth_url,
            "message": "Visit the authorization URL to grant access to your YouTube Analytics data"
        }
        
    except Exception as e:
        logger.error(f"Failed to start YouTube authorization: {e}")
        raise HTTPException(status_code=500, detail="Failed to start authorization process")


@router.get("/callback")
async def youtube_oauth_callback(request: Request, db: Session = Depends(get_db)):
    """Handle the OAuth callback from YouTube."""
    try:
        # Get authorization code from query parameters
        code = request.query_params.get('code')
        error = request.query_params.get('error')
        
        if error:
            logger.error(f"YouTube OAuth error: {error}")
            raise HTTPException(status_code=400, detail=f"Authorization failed: {error}")
        
        if not code:
            raise HTTPException(status_code=400, detail="No authorization code received")
        
        # Exchange code for tokens
        youtube_analytics = YouTubeAnalyticsService(db)
        
        base_url = str(request.base_url).rstrip('/')
        redirect_uri = f"{base_url}/api/v1/youtube-auth/callback"
        
        token_data = youtube_analytics.exchange_code_for_tokens(code, redirect_uri)
        
        # Get channel information to identify the channel
        from app.services.youtube import YouTubeDataService
        youtube_data = YouTubeDataService(db, access_token=token_data['access_token'])
        
        # Get the authenticated user's channel
        channel_info = youtube_data.get_channel_info()  # This will get the authenticated user's channel
        channel_id = channel_info.get('id')
        
        if not channel_id:
            raise HTTPException(status_code=400, detail="Could not identify YouTube channel")
        
        # Store or update tokens in database
        existing_token = db.query(YouTubeOAuthToken).filter(
            YouTubeOAuthToken.channel_id == channel_id
        ).first()
        
        if existing_token:
            # Update existing token
            existing_token.access_token = token_data['access_token']
            existing_token.refresh_token = token_data.get('refresh_token')
            existing_token.expires_at = datetime.fromisoformat(token_data['expires_at']) if token_data.get('expires_at') else None
            existing_token.is_active = True
            existing_token.last_refreshed = datetime.utcnow()
            existing_token.error_count = 0
            existing_token.last_error = None
            existing_token.updated_at = datetime.utcnow()
        else:
            # Create new token record
            new_token = YouTubeOAuthToken(
                channel_id=channel_id,
                access_token=token_data['access_token'],
                refresh_token=token_data.get('refresh_token'),
                expires_at=datetime.fromisoformat(token_data['expires_at']) if token_data.get('expires_at') else None,
                scope='https://www.googleapis.com/auth/youtube.readonly,https://www.googleapis.com/auth/yt-analytics.readonly',
                is_active=True,
                last_refreshed=datetime.utcnow()
            )
            db.add(new_token)
        
        db.commit()
        
        logger.info(f"Successfully stored YouTube OAuth tokens for channel: {channel_id}")
        
        # Redirect to frontend with success message
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(
            url=f"{frontend_url}?youtube_auth=success&channel_id={channel_id}",
            status_code=302
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to handle YouTube OAuth callback: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete authorization")


@router.get("/status")
async def get_youtube_auth_status(db: Session = Depends(get_db)):
    """Check the current YouTube authentication status."""
    try:
        # Get all active tokens
        tokens = db.query(YouTubeOAuthToken).filter(
            YouTubeOAuthToken.is_active == True
        ).all()
        
        if not tokens:
            return {
                "status": "not_authenticated",
                "message": "No YouTube Analytics access configured",
                "channels": []
            }
        
        channel_status = []
        for token in tokens:
            status = {
                "channel_id": token.channel_id,
                "is_expired": token.is_expired(),
                "needs_refresh": token.needs_refresh(),
                "last_refreshed": token.last_refreshed.isoformat() if token.last_refreshed else None,
                "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                "error_count": token.error_count,
                "last_error": token.last_error
            }
            channel_status.append(status)
        
        return {
            "status": "authenticated",
            "message": f"YouTube Analytics access configured for {len(tokens)} channel(s)",
            "channels": channel_status
        }
        
    except Exception as e:
        logger.error(f"Failed to get YouTube auth status: {e}")
        raise HTTPException(status_code=500, detail="Failed to check authentication status")


@router.post("/refresh")
async def refresh_youtube_tokens(db: Session = Depends(get_db)):
    """Manually refresh YouTube OAuth tokens."""
    try:
        tokens = db.query(YouTubeOAuthToken).filter(
            YouTubeOAuthToken.is_active == True,
            YouTubeOAuthToken.refresh_token.isnot(None)
        ).all()
        
        if not tokens:
            raise HTTPException(status_code=404, detail="No refresh tokens found")
        
        youtube_analytics = YouTubeAnalyticsService(db)
        refreshed_count = 0
        errors = []
        
        for token in tokens:
            try:
                new_token_data = youtube_analytics.refresh_access_token(token.refresh_token)
                
                # Update token in database
                token.access_token = new_token_data['access_token']
                token.expires_at = datetime.fromisoformat(new_token_data['expires_at']) if new_token_data.get('expires_at') else None
                token.last_refreshed = datetime.utcnow()
                token.error_count = 0
                token.last_error = None
                token.updated_at = datetime.utcnow()
                
                refreshed_count += 1
                logger.info(f"Refreshed token for channel: {token.channel_id}")
                
            except Exception as e:
                error_msg = f"Failed to refresh token for channel {token.channel_id}: {str(e)}"
                errors.append(error_msg)
                
                # Update error tracking
                token.error_count += 1
                token.last_error = str(e)
                token.updated_at = datetime.utcnow()
                
                # Deactivate token if too many errors
                if token.error_count >= 5:
                    token.is_active = False
                    logger.warning(f"Deactivated token for channel {token.channel_id} due to repeated errors")
        
        db.commit()
        
        return {
            "status": "success",
            "refreshed_count": refreshed_count,
            "total_tokens": len(tokens),
            "errors": errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh YouTube tokens: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh tokens")


@router.delete("/revoke")
async def revoke_youtube_access(channel_id: str = None, db: Session = Depends(get_db)):
    """Revoke YouTube Analytics access for a channel."""
    try:
        query = db.query(YouTubeOAuthToken).filter(YouTubeOAuthToken.is_active == True)
        
        if channel_id:
            query = query.filter(YouTubeOAuthToken.channel_id == channel_id)
        
        tokens = query.all()
        
        if not tokens:
            raise HTTPException(status_code=404, detail="No active tokens found")
        
        # Deactivate tokens
        for token in tokens:
            token.is_active = False
            token.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Revoked access for {len(tokens)} token(s)",
            "revoked_channels": [token.channel_id for token in tokens]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke YouTube access: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke access")
