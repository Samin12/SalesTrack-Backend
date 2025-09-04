"""
Authentication service for Google OAuth 2.0 integration.
"""
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from loguru import logger

from app.core.config import settings, get_google_oauth_config
from app.models.auth import OAuthToken, UserSession
from app.core.database import get_db


class GoogleOAuthService:
    """Service for handling Google OAuth 2.0 authentication."""
    
    def __init__(self):
        self.oauth_config = get_google_oauth_config()
        self.flow = None
        self._initialize_flow()
    
    def _initialize_flow(self):
        """Initialize the OAuth flow."""
        try:
            client_config = {
                "web": {
                    "client_id": self.oauth_config["client_id"],
                    "client_secret": self.oauth_config["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.oauth_config["redirect_uri"]]
                }
            }
            
            self.flow = Flow.from_client_config(
                client_config,
                scopes=self.oauth_config["scopes"]
            )
            self.flow.redirect_uri = self.oauth_config["redirect_uri"]
            
        except Exception as e:
            logger.error(f"Failed to initialize OAuth flow: {e}")
            raise
    
    def get_authorization_url(self) -> str:
        """Get the authorization URL for OAuth flow."""
        try:
            authorization_url, _ = self.flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            return authorization_url
        except Exception as e:
            logger.error(f"Failed to get authorization URL: {e}")
            raise
    
    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access tokens."""
        try:
            self.flow.fetch_token(code=code)
            credentials = self.flow.credentials
            
            return {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_type": "Bearer",
                "expires_at": credentials.expiry,
                "scope": " ".join(credentials.scopes) if credentials.scopes else ""
            }
        except Exception as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
            raise
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an access token using refresh token."""
        try:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.oauth_config["client_id"],
                client_secret=self.oauth_config["client_secret"]
            )
            
            credentials.refresh(Request())
            
            return {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_type": "Bearer",
                "expires_at": credentials.expiry,
                "scope": " ".join(credentials.scopes) if credentials.scopes else ""
            }
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Google API."""
        try:
            credentials = Credentials(token=access_token)
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            return user_info
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise
    
    def validate_token(self, access_token: str) -> bool:
        """Validate an access token."""
        try:
            credentials = Credentials(token=access_token)
            credentials.refresh(Request())
            return True
        except Exception:
            return False


class JWTService:
    """Service for handling JWT tokens."""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None


class AuthService:
    """Main authentication service."""
    
    def __init__(self, db: Session):
        self.db = db
        self.google_oauth = GoogleOAuthService()
        self.jwt_service = JWTService()
    
    def save_oauth_token(self, user_id: str, email: str, token_data: Dict[str, Any]) -> OAuthToken:
        """Save OAuth token to database."""
        try:
            # Check if token already exists
            existing_token = self.db.query(OAuthToken).filter(
                OAuthToken.user_id == user_id
            ).first()
            
            if existing_token:
                # Update existing token
                existing_token.access_token = token_data["access_token"]
                existing_token.refresh_token = token_data.get("refresh_token")
                existing_token.expires_at = token_data.get("expires_at")
                existing_token.scope = token_data.get("scope", "")
                existing_token.is_active = True
                existing_token.is_revoked = False
                token = existing_token
            else:
                # Create new token
                token = OAuthToken(
                    user_id=user_id,
                    email=email,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token"),
                    token_type=token_data.get("token_type", "Bearer"),
                    expires_at=token_data.get("expires_at"),
                    scope=token_data.get("scope", ""),
                    provider="google"
                )
                self.db.add(token)
            
            self.db.commit()
            self.db.refresh(token)
            return token
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save OAuth token: {e}")
            raise
    
    def get_valid_token(self, user_id: str) -> Optional[str]:
        """Get a valid access token for a user."""
        try:
            token = self.db.query(OAuthToken).filter(
                OAuthToken.user_id == user_id,
                OAuthToken.is_active == True,
                OAuthToken.is_revoked == False
            ).first()
            
            if not token:
                return None
            
            # Check if token is expired
            if token.expires_at and token.expires_at <= datetime.utcnow():
                # Try to refresh token
                if token.refresh_token:
                    try:
                        new_token_data = self.google_oauth.refresh_access_token(token.refresh_token)
                        self.save_oauth_token(user_id, token.email, new_token_data)
                        return new_token_data["access_token"]
                    except Exception as e:
                        logger.error(f"Failed to refresh token: {e}")
                        return None
                else:
                    return None
            
            return token.access_token
            
        except Exception as e:
            logger.error(f"Failed to get valid token: {e}")
            return None
