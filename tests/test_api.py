"""
Test cases for the YouTube Analytics API.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.main import app
from app.core.database import get_db, Base
from app.models.channel import Channel, ChannelMetrics
from app.models.video import Video, VideoMetrics

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture
def test_db():
    """Create test database session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_channel(test_db):
    """Create sample channel for testing."""
    channel = Channel(
        channel_id="UC_test_channel_id",
        channel_handle="@TestChannel",
        channel_name="Test Channel",
        channel_description="A test channel for analytics",
        subscriber_count=10000,
        video_count=50,
        view_count=1000000,
        last_updated=datetime.utcnow()
    )
    test_db.add(channel)
    test_db.commit()
    test_db.refresh(channel)
    return channel


@pytest.fixture
def sample_video(test_db, sample_channel):
    """Create sample video for testing."""
    video = Video(
        video_id="test_video_id_123",
        channel_id=sample_channel.channel_id,
        title="Test Video Title",
        description="A test video description",
        published_at=datetime.utcnow(),
        duration="PT10M30S",
        duration_seconds=630,
        view_count=50000,
        like_count=1000,
        comment_count=100,
        last_updated=datetime.utcnow()
    )
    test_db.add(video)
    test_db.commit()
    test_db.refresh(video)
    return video


class TestHealthEndpoints:
    """Test health and basic endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint returns API information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "YouTube Analytics API"
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    def test_get_google_auth_url(self):
        """Test getting Google OAuth URL."""
        response = client.get("/api/v1/auth/google")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "https://accounts.google.com" in data["authorization_url"]
    
    def test_auth_status(self):
        """Test authentication status endpoint."""
        response = client.get("/api/v1/auth/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestAnalyticsEndpoints:
    """Test analytics endpoints."""
    
    def test_channel_overview_not_found(self):
        """Test channel overview when channel doesn't exist."""
        # This will fail because we don't have the actual channel in test DB
        response = client.get("/api/v1/analytics/channel/overview")
        # Should return 500 because it tries to fetch from YouTube API
        assert response.status_code == 500
    
    def test_videos_endpoint_empty(self):
        """Test videos endpoint with no data."""
        response = client.get("/api/v1/analytics/videos")
        assert response.status_code == 200
        data = response.json()
        assert "total_videos" in data
        assert data["total_videos"] == 0
        assert "videos" in data
        assert isinstance(data["videos"], list)
    
    def test_analytics_overview_not_found(self):
        """Test analytics overview when no data exists."""
        response = client.get("/api/v1/analytics/overview")
        # Should return 404 because channel doesn't exist
        assert response.status_code == 404


class TestDataModels:
    """Test data models and database operations."""
    
    def test_create_channel(self, test_db):
        """Test creating a channel in database."""
        channel = Channel(
            channel_id="UC_test_123",
            channel_handle="@TestHandle",
            channel_name="Test Channel Name",
            subscriber_count=5000,
            video_count=25,
            view_count=500000
        )
        test_db.add(channel)
        test_db.commit()
        
        # Verify channel was created
        saved_channel = test_db.query(Channel).filter(
            Channel.channel_id == "UC_test_123"
        ).first()
        assert saved_channel is not None
        assert saved_channel.channel_name == "Test Channel Name"
        assert saved_channel.subscriber_count == 5000
    
    def test_create_video(self, test_db, sample_channel):
        """Test creating a video in database."""
        video = Video(
            video_id="video_test_456",
            channel_id=sample_channel.channel_id,
            title="Test Video",
            published_at=datetime.utcnow(),
            view_count=10000,
            like_count=500,
            comment_count=50
        )
        test_db.add(video)
        test_db.commit()
        
        # Verify video was created
        saved_video = test_db.query(Video).filter(
            Video.video_id == "video_test_456"
        ).first()
        assert saved_video is not None
        assert saved_video.title == "Test Video"
        assert saved_video.channel_id == sample_channel.channel_id
    
    def test_channel_metrics(self, test_db, sample_channel):
        """Test creating channel metrics."""
        metrics = ChannelMetrics(
            channel_id=sample_channel.channel_id,
            date=datetime.utcnow(),
            subscriber_count=10500,
            view_count=1050000,
            subscriber_growth=500,
            subscriber_growth_rate=5.0,
            view_growth=50000,
            view_growth_rate=5.0
        )
        test_db.add(metrics)
        test_db.commit()
        
        # Verify metrics were created
        saved_metrics = test_db.query(ChannelMetrics).filter(
            ChannelMetrics.channel_id == sample_channel.channel_id
        ).first()
        assert saved_metrics is not None
        assert saved_metrics.subscriber_growth == 500
        assert saved_metrics.subscriber_growth_rate == 5.0


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_video_id(self):
        """Test requesting analytics for invalid video ID."""
        response = client.get("/api/v1/analytics/videos/invalid_video_id")
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "error"
    
    def test_invalid_date_range(self):
        """Test analytics with invalid date range."""
        response = client.get("/api/v1/analytics/channel/growth?days=0")
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__])
