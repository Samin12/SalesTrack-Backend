# Railway Deployment Guide

## 🚀 Quick Railway Deployment

### Prerequisites
- Railway account and CLI installed
- GitHub repository connected to Railway
- Required API keys and credentials

## 📁 Files Created for Railway

This deployment includes the following Railway-specific files:

1. **`railway.json`** - Railway configuration
2. **`frontend/.env.production`** - Frontend production environment
3. **`backend/.env.railway`** - Backend environment template
4. **`backend/railway-start.sh`** - Backend startup script
5. **`Procfile`** - Railway process definition

## 🔧 Backend Deployment

### Step 1: Set Environment Variables in Railway Dashboard

Go to your **backend service** in Railway and set these variables:

```env
# Core Configuration
ENVIRONMENT=production
DATABASE_URL=sqlite:///./youtube_analytics.db
DEBUG=false
PYTHON_VERSION=3.11

# CORS (Update after frontend deployment)
CORS_ORIGINS=*

# JWT (Generate secure key)
SECRET_KEY=your_super_secret_jwt_key_here_change_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Google OAuth (REQUIRED - Get from Google Cloud Console)
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
GOOGLE_REDIRECT_URI=https://your-backend-service.railway.app/auth/google/callback

# YouTube API (REQUIRED - Get from Google Cloud Console)
YOUTUBE_API_KEY=your_youtube_api_key_here
YOUTUBE_CHANNEL_ID=UCYourChannelIdHere
YOUTUBE_CHANNEL_HANDLE=@SaminYasar_

# ScrapeCreators API
SCRAPECREATORS_API_KEY=wHAmZcysPNY6yDhX0impv2Lv5dg1
SCRAPECREATORS_BASE_URL=https://api.scrapecreators.com

# GA4 Configuration
GA4_PROPERTY_ID=403263912
GA4_MEASUREMENT_ID=G-EHL8BJZJ9E
GA4_API_SECRET=BXNpXtlBRP2ckCNBntI7xw

# Base URL (Update with your Railway backend URL)
BASE_URL=https://your-backend-service.railway.app
```

### Step 2: Deploy Backend
Railway will automatically deploy when you push to GitHub.

## 🌐 Frontend Deployment

### Step 1: Update API URL
After backend deployment, update `frontend/.env.production`:

```env
NEXT_PUBLIC_API_URL=https://your-actual-backend-url.railway.app
```

### Step 2: Set Frontend Variables in Railway Dashboard

```env
NODE_ENV=production
NODE_VERSION=18.17.0
NEXT_TELEMETRY_DISABLED=1
NEXT_PUBLIC_APP_NAME=YouTube Analytics
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_YOUTUBE_CHANNEL_HANDLE=@SaminYasar_
NEXT_PUBLIC_YOUTUBE_CHANNEL_URL=https://www.youtube.com/@SaminYasar_
```

## 🔑 Required API Keys

You need to obtain these from Google Cloud Console:

1. **Google OAuth Client ID & Secret**
   - Go to Google Cloud Console
   - Enable YouTube Data API v3
   - Create OAuth 2.0 credentials
   - Add your Railway backend URL to authorized redirect URIs

2. **YouTube API Key**
   - Create an API key in Google Cloud Console
   - Restrict it to YouTube Data API v3

## 🔄 Deployment Process

1. **Commit and push** all the new files to GitHub
2. **Railway will auto-deploy** both services
3. **Update environment variables** with actual URLs after deployment
4. **Test the deployment** using the provided URLs

## 🌐 Expected URLs

After deployment, you'll have:
- **Backend**: `https://youtube-analytics-backend-production-[id].railway.app`
- **Frontend**: `https://youtube-analytics-frontend-production-[id].railway.app`
- **API Docs**: `https://your-backend-url.railway.app/docs`

## 🔍 Troubleshooting

### Build Failures
1. Check Railway logs for specific errors
2. Verify all environment variables are set
3. Ensure API keys are valid and have proper permissions

### CORS Issues
Update `CORS_ORIGINS` in backend to include your frontend URL:
```env
CORS_ORIGINS=https://your-frontend-url.railway.app,*
```

### Database Issues
The SQLite database will be created automatically by the startup script.

## 📝 Post-Deployment Steps

1. **Test API endpoints** at `/docs`
2. **Verify frontend** can connect to backend
3. **Test Google OAuth** login flow
4. **Check YouTube API** integration
5. **Monitor Railway logs** for any issues

## 🔒 Security Notes

1. **Replace default SECRET_KEY** with a secure random string
2. **Restrict CORS_ORIGINS** to your actual frontend URL
3. **Keep API keys secure** and never commit them to git
4. **Monitor Railway usage** to avoid unexpected charges
