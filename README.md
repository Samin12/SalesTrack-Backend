# YouTube Analytics Backend

FastAPI backend service for the YouTube Analytics Dashboard. This service handles YouTube API integration, Google Analytics 4 tracking, UTM link management, and analytics data processing.

## 🚀 Features

- **YouTube API Integration**: Fetch channel statistics, video data, and performance metrics
- **Google Analytics 4**: Track UTM clicks and user behavior
- **UTM Link Management**: Create, track, and analyze UTM campaign links
- **Database Support**: SQLite for development, PostgreSQL/Supabase for production
- **Authentication**: Google OAuth integration for YouTube data access
- **Rate Limiting**: Built-in API rate limiting and caching
- **Real-time Analytics**: Live data synchronization and reporting

## 📋 Prerequisites

- Python 3.9+
- YouTube Data API v3 key
- Google OAuth credentials
- Google Analytics 4 property (optional)
- Supabase account (for production)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/AI-Answer/youtube-analytics-backend.git
cd youtube-analytics-backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Copy the example environment file and configure your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your credentials - see `.env.example` for all required variables.

## 🚀 Running the Application

### Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📚 API Documentation

### Core Endpoints

- `GET /health` - Health check
- `GET /api/v1/analytics/overview` - Complete analytics overview
- `GET /api/v1/analytics/channel/overview` - Channel statistics
- `GET /api/v1/analytics/videos` - Video performance data
- `POST /api/v1/analytics/sync` - Sync fresh data from YouTube

### UTM Tracking

- `POST /api/v1/utm-links` - Create UTM tracking link
- `GET /api/v1/utm-links` - List all UTM links
- `GET /api/v1/utm-links/{id}/analytics` - UTM link analytics
- `GET /api/v1/r/{id}` - Redirect UTM link (tracks clicks)

### Authentication

- `GET /api/v1/auth/google` - Google OAuth login
- `GET /api/v1/auth/google/callback` - OAuth callback
- `POST /api/v1/auth/refresh` - Refresh access token

## 🚢 Deployment

### Railway Deployment

1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard (see .env.example)
3. Deploy automatically on git push

See `RAILWAY_DEPLOYMENT.md` for detailed deployment instructions.

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- Create an issue on GitHub
- Check the API documentation at `/docs`
- Review the deployment guides in the repository
