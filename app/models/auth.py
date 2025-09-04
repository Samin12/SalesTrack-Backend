"""
Authentication models for OAuth tokens and user sessions.
"""
from sqlalchemy import Column, String, DateTime, Text, Boolean
from app.models.base import BaseModel


class OAuthToken(BaseModel):
    """OAuth token storage for Google/YouTube API access."""
    __tablename__ = "oauth_tokens"
    
    # User identification
    user_id = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(200), index=True)
    
    # OAuth tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_type = Column(String(50), default="Bearer")
    
    # Token metadata
    expires_at = Column(DateTime(timezone=True))
    scope = Column(Text)  # Space-separated scopes
    
    # Provider information
    provider = Column(String(50), default="google")
    provider_user_id = Column(String(100))  # Google user ID
    
    # Status
    is_active = Column(Boolean, default=True)
    is_revoked = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<OAuthToken(user_id={self.user_id}, provider={self.provider}, active={self.is_active})>"


class UserSession(BaseModel):
    """User session management."""
    __tablename__ = "user_sessions"
    
    # Session identification
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(String(100), nullable=False, index=True)
    
    # Session data
    access_token = Column(Text, nullable=False)  # JWT token for API access
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Session metadata
    ip_address = Column(String(50))
    user_agent = Column(Text)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<UserSession(session_id={self.session_id}, user_id={self.user_id}, active={self.is_active})>"
