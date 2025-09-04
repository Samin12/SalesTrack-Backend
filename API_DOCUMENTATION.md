# YouTube Analytics API Documentation

## Overview

The YouTube Analytics API provides comprehensive analytics data for YouTube channels and videos, with features for tracking growth, performance metrics, and website traffic conversion.

## Base URL

```
http://localhost:8000
```

## Authentication

The API uses Google OAuth 2.0 for accessing YouTube data. Some endpoints require authentication while others provide public data.

### Authentication Flow

1. **Get Authorization URL**
   ```
   GET /api/v1/auth/google
   ```
   Returns the Google OAuth authorization URL.

2. **OAuth Callback**
   ```
   GET /api/v1/auth/google/callback?code={authorization_code}
   ```
   Exchanges the authorization code for access tokens.

3. **Use JWT Token**
   Include the returned JWT token in the Authorization header:
   ```
   Authorization: Bearer {jwt_token}
   ```

## API Endpoints

### Health & Status

#### GET /
Returns basic API information.

**Response:**
```json
{
  "message": "YouTube Analytics API",
  "version": "1.0.0",
  "docs": "/docs",
  "redoc": "/redoc",
  "api_v1": "/api/v1"
}
```

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "1.0.0"
}
```

### Authentication Endpoints

#### GET /api/v1/auth/google
Get Google OAuth authorization URL.

**Response:**
```json
{
  "status": "success",
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
  "message": "Visit the authorization URL to authenticate with Google",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### GET /api/v1/auth/google/callback
Handle OAuth callback (typically called by Google).

**Parameters:**
- `code` (query): Authorization code from Google

**Response:**
```json
{
  "status": "success",
  "access_token": "jwt_token_here",
  "token_type": "bearer",
  "message": "Authentication successful",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Analytics Endpoints

#### GET /api/v1/analytics/channel/overview
Get channel overview with current metrics.

**Response:**
```json
{
  "channel_id": "UC_channel_id",
  "channel_name": "Channel Name",
  "channel_handle": "@ChannelHandle",
  "subscriber_count": 10000,
  "video_count": 50,
  "view_count": 1000000,
  "last_updated": "2024-01-01T12:00:00Z"
}
```

#### GET /api/v1/analytics/channel/growth
Get channel growth metrics over time.

**Parameters:**
- `start_date` (query, optional): Start date (ISO format)
- `end_date` (query, optional): End date (ISO format)
- `days` (query, optional): Number of days to analyze (default: 30)

**Response:**
```json
{
  "status": "success",
  "channel_id": "UC_channel_id",
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-01-31T23:59:59Z",
  "current_metrics": {
    "date": "2024-01-31T12:00:00Z",
    "subscriber_count": 10500,
    "subscriber_growth": 500,
    "subscriber_growth_rate": 5.0,
    "view_count": 1050000,
    "view_growth": 50000,
    "view_growth_rate": 5.0
  },
  "historical_data": [...],
  "summary": {
    "period_days": 30,
    "total_subscriber_growth": 500,
    "total_view_growth": 50000,
    "average_daily_subscriber_growth": 16.67,
    "average_daily_view_growth": 1666.67
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### GET /api/v1/analytics/videos
Get videos with performance metrics.

**Parameters:**
- `page` (query, optional): Page number (default: 1)
- `limit` (query, optional): Items per page (default: 50, max: 100)
- `sort_by` (query, optional): Sort field (published_at, view_count, growth_rate)
- `order` (query, optional): Sort order (asc, desc)
- `start_date` (query, optional): Filter by date range
- `end_date` (query, optional): Filter by date range
- `days` (query, optional): Number of days to analyze

**Response:**
```json
{
  "status": "success",
  "total_videos": 50,
  "videos": [
    {
      "video_id": "video_id_123",
      "title": "Video Title",
      "published_at": "2024-01-01T12:00:00Z",
      "view_count": 50000,
      "like_count": 1000,
      "comment_count": 100,
      "duration_seconds": 630
    }
  ],
  "top_performing": [...],
  "fastest_growing": [...],
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### GET /api/v1/analytics/videos/{video_id}
Get detailed performance metrics for a specific video.

**Parameters:**
- `video_id` (path): YouTube video ID
- `start_date` (query, optional): Start date for metrics
- `end_date` (query, optional): End date for metrics
- `days` (query, optional): Number of days to analyze

**Response:**
```json
{
  "status": "success",
  "video_id": "video_id_123",
  "video_info": {
    "video_id": "video_id_123",
    "title": "Video Title",
    "published_at": "2024-01-01T12:00:00Z",
    "view_count": 50000,
    "like_count": 1000,
    "comment_count": 100,
    "duration_seconds": 630
  },
  "current_metrics": {
    "date": "2024-01-31T12:00:00Z",
    "view_count": 52000,
    "view_growth": 2000,
    "view_growth_rate": 4.0,
    "like_count": 1050,
    "comment_count": 110,
    "engagement_rate": 2.23
  },
  "historical_data": [...],
  "growth_analysis": {
    "total_view_growth": 2000,
    "average_daily_views": 66.67,
    "peak_growth_day": "2024-01-15T00:00:00Z",
    "engagement_trend": "stable"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### GET /api/v1/analytics/traffic/website
Get website traffic data from YouTube sources.

**Parameters:**
- `start_date` (query, optional): Start date
- `end_date` (query, optional): End date
- `days` (query, optional): Number of days to analyze

**Response:**
```json
{
  "status": "success",
  "period_start": "2024-01-01T00:00:00Z",
  "period_end": "2024-01-31T23:59:59Z",
  "total_clicks": 5000,
  "total_page_views": 4500,
  "average_ctr": 2.5,
  "traffic_data": [...],
  "top_sources": [
    {
      "source": "youtube_channel",
      "clicks": 2000,
      "page_views": 1800,
      "conversion_rate": 90.0
    }
  ],
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### GET /api/v1/analytics/overview
Get comprehensive analytics overview.

**Response:**
```json
{
  "status": "success",
  "channel_overview": {...},
  "recent_growth": {...},
  "top_videos": [...],
  "traffic_summary": {
    "total_clicks_last_30_days": 5000,
    "total_page_views_last_30_days": 4500,
    "top_traffic_source": "youtube_channel"
  },
  "key_insights": [
    "Channel has 10,000 subscribers",
    "Total of 50 videos published",
    "Most popular video has 100,000 views",
    "Growing by 500 subscribers recently"
  ],
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### POST /api/v1/analytics/sync
Manually trigger analytics data synchronization.

**Response:**
```json
{
  "status": "success",
  "message": "Analytics data synchronized successfully. Processed 25 videos.",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "status": "error",
  "message": "Error description",
  "error_code": "ERROR_CODE",
  "details": {},
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Common Error Codes

- `YOUTUBE_API_ERROR`: Error from YouTube Data API
- `SCRAPECREATORS_API_ERROR`: Error from ScrapeCreators API
- `AUTHENTICATION_ERROR`: Authentication failed
- `DATA_NOT_FOUND`: Requested data not found
- `VALIDATION_ERROR`: Request validation failed
- `INTERNAL_SERVER_ERROR`: Unexpected server error

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized
- `404`: Not Found
- `422`: Validation Error
- `429`: Rate Limited
- `500`: Internal Server Error

## Rate Limiting

The API implements rate limiting:
- Default: 60 requests per minute per IP
- Rate limit headers are included in responses
- Exceeded limits return HTTP 429

## Caching

The API uses Redis caching for improved performance:
- Channel data: 30 minutes
- Video metrics: 5 minutes
- Analytics overview: 2 hours
- Traffic data: 24 hours

## Interactive Documentation

Visit these URLs when the server is running:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
