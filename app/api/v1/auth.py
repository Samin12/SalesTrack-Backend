"""
Authentication API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.services.auth import AuthService, GoogleOAuthService, JWTService
from app.api.v1.schemas import AuthURLResponse, TokenResponse, BaseResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/google", response_model=AuthURLResponse)
async def get_google_auth_url():
    """Get Google OAuth authorization URL."""
    try:
        oauth_service = GoogleOAuthService()
        auth_url = oauth_service.get_authorization_url()
        
        return AuthURLResponse(
            authorization_url=auth_url,
            message="Visit the authorization URL to authenticate with Google"
        )
    except Exception as e:
        logger.error(f"Failed to get Google auth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")


@router.get("/google/callback")
async def google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    db: Session = Depends(get_db)
):
    """Handle Google OAuth callback."""
    try:
        oauth_service = GoogleOAuthService()
        auth_service = AuthService(db)
        
        # Exchange code for tokens
        token_data = oauth_service.exchange_code_for_tokens(code)
        
        # Get user info
        user_info = oauth_service.get_user_info(token_data["access_token"])
        user_id = user_info.get("id")
        email = user_info.get("email")
        
        if not user_id or not email:
            raise HTTPException(status_code=400, detail="Failed to get user information")
        
        # Save OAuth token
        oauth_token = auth_service.save_oauth_token(user_id, email, token_data)
        
        # Create JWT token for API access
        jwt_token = JWTService.create_access_token(
            data={"sub": user_id, "email": email}
        )
        
        # In a real application, you might redirect to your frontend with the token
        # For now, we'll return the token directly
        return TokenResponse(
            access_token=jwt_token,
            message="Authentication successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """Refresh an access token."""
    try:
        oauth_service = GoogleOAuthService()
        
        # Refresh the token
        new_token_data = oauth_service.refresh_access_token(refresh_token)
        
        # Create new JWT token
        jwt_token = JWTService.create_access_token(
            data={"sub": "user_id"}  # In real app, get from refresh token
        )
        
        return TokenResponse(
            access_token=jwt_token,
            message="Token refreshed successfully"
        )
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=401, detail="Failed to refresh token")


@router.post("/logout", response_model=BaseResponse)
async def logout(
    request: Request,
    db: Session = Depends(get_db)
):
    """Logout user and revoke tokens."""
    try:
        # In a real application, you would:
        # 1. Extract user ID from JWT token
        # 2. Mark OAuth tokens as revoked in database
        # 3. Add JWT token to blacklist
        
        return BaseResponse(message="Logged out successfully")
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/status", response_model=BaseResponse)
async def auth_status(
    request: Request,
    db: Session = Depends(get_db)
):
    """Check authentication status."""
    try:
        # In a real application, you would verify the JWT token
        # and return user authentication status
        
        return BaseResponse(
            message="Authentication status check",
            # Add user info here
        )
        
    except Exception as e:
        logger.error(f"Auth status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check auth status")
