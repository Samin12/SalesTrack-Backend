"""
Google Analytics 4 (GA4) Integration Service

This service handles:
1. Sending UTM click events to GA4 via Measurement Protocol
2. Fetching analytics data from GA4 Data API
3. Syncing GA4 data with local database
"""

import os
import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import httpx
import requests
from loguru import logger
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    Dimension,
    Metric,
    DateRange,
    FilterExpression,
    Filter,
)
from google.oauth2 import service_account
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.utm_link import UTMLink, LinkClick
from app.core.database import get_db


class GA4Service:
    """Google Analytics 4 integration service"""
    
    def __init__(self):
        self.property_id = settings.GA4_PROPERTY_ID
        self.measurement_id = settings.GA4_MEASUREMENT_ID
        self.api_secret = settings.GA4_API_SECRET
        self.service_account_path = settings.GA4_SERVICE_ACCOUNT_PATH
        self.measurement_protocol_url = "https://www.google-analytics.com/mp/collect"
        self.client = None
        
        # Initialize GA4 client if credentials are available
        if self.service_account_path and os.path.exists(self.service_account_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_path,
                    scopes=["https://www.googleapis.com/auth/analytics.readonly"]
                )
                self.client = BetaAnalyticsDataClient(credentials=credentials)
                logger.info("GA4 client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize GA4 client: {e}")
        else:
            logger.warning("GA4 service account credentials not found")

    async def send_utm_click_event(
        self,
        utm_link: UTMLink,
        user_agent: str = None,
        ip_address: str = None,
        referrer: str = None
    ) -> bool:
        """
        Send UTM click event to GA4 via Measurement Protocol
        
        Args:
            utm_link: UTM link that was clicked
            user_agent: User agent string
            ip_address: Client IP address
            referrer: Referrer URL
            
        Returns:
            bool: True if event was sent successfully
        """
        if not self.measurement_id or not self.api_secret:
            logger.warning("GA4 Measurement Protocol not configured")
            return False
            
        try:
            # Generate client ID (should be persistent per user in production)
            client_id = str(uuid.uuid4())
            
            # Prepare event data
            event_data = {
                "client_id": client_id,
                "events": [{
                    "name": "utm_link_click",
                    "params": {
                        "link_url": utm_link.destination_url,
                        "video_id": utm_link.video_id,
                        "utm_source": utm_link.utm_source,
                        "utm_medium": utm_link.utm_medium,
                        "utm_campaign": utm_link.utm_campaign,
                        "utm_content": utm_link.utm_content or "",
                        "utm_term": utm_link.utm_term or "",
                        "link_id": str(utm_link.id),
                        "event_category": "UTM Tracking",
                        "value": 1
                    }
                }]
            }
            
            # Add user context if available
            if user_agent:
                event_data["user_properties"] = {
                    "user_agent": {"value": user_agent}
                }
            
            # Send event to GA4 (with debug mode)
            params = {
                "measurement_id": self.measurement_id,
                "api_secret": self.api_secret
            }

            # Use production endpoint
            url = "https://www.google-analytics.com/mp/collect"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    params=params,
                    json=event_data,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": user_agent or "YouTube-Analytics-Dashboard/1.0"
                    }
                )
                
            if response.status_code in [200, 204]:
                logger.info(f"GA4 event sent successfully for UTM link {utm_link.id}")
                if response.text:
                    logger.info(f"GA4 debug response: {response.text}")
                return True
            else:
                logger.error(f"GA4 event failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending GA4 event: {e}")
            return False

    def fetch_utm_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        utm_source: str = None,
        utm_campaign: str = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch UTM analytics data from GA4
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            utm_source: Filter by UTM source
            utm_campaign: Filter by UTM campaign
            
        Returns:
            List of analytics data
        """
        if not self.client or not self.property_id:
            logger.warning("GA4 client not initialized")
            return []
            
        try:
            # Build dimensions and metrics
            dimensions = [
                Dimension(name="customEvent:utm_source"),
                Dimension(name="customEvent:utm_medium"),
                Dimension(name="customEvent:utm_campaign"),
                Dimension(name="customEvent:utm_content"),
                Dimension(name="customEvent:utm_term"),
                Dimension(name="customEvent:destination_url"),
                Dimension(name="customEvent:video_id"),
                Dimension(name="customEvent:link_id"),
                Dimension(name="date"),
            ]
            
            metrics = [
                Metric(name="eventCount"),
                Metric(name="totalUsers"),
                Metric(name="sessions"),
            ]
            
            # Build date range
            date_range = DateRange(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
            
            # Build filter if needed (simplified for now)
            dimension_filter = None
            # Note: Advanced filtering will be implemented once GA4 is properly configured
            
            # Create request
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=dimensions,
                metrics=metrics,
                date_ranges=[date_range],
                dimension_filter=dimension_filter,
                limit=10000
            )
            
            # Run report
            response = self.client.run_report(request=request)
            
            # Process results
            results = []
            for row in response.rows:
                result = {
                    "utm_source": row.dimension_values[0].value,
                    "utm_medium": row.dimension_values[1].value,
                    "utm_campaign": row.dimension_values[2].value,
                    "utm_content": row.dimension_values[3].value,
                    "utm_term": row.dimension_values[4].value,
                    "destination_url": row.dimension_values[5].value,
                    "video_id": row.dimension_values[6].value,
                    "link_id": row.dimension_values[7].value,
                    "date": row.dimension_values[8].value,
                    "event_count": int(row.metric_values[0].value),
                    "total_users": int(row.metric_values[1].value),
                    "sessions": int(row.metric_values[2].value),
                }
                results.append(result)
                
            logger.info(f"Fetched {len(results)} GA4 analytics records")
            return results
            
        except Exception as e:
            logger.error(f"Error fetching GA4 analytics: {e}")
            return []

    async def sync_ga4_data_to_database(self, days_back: int = 7) -> Dict[str, int]:
        """
        Sync GA4 analytics data to local database
        
        Args:
            days_back: Number of days to sync
            
        Returns:
            Dict with sync statistics
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Fetch GA4 data
        ga4_data = self.fetch_utm_analytics(start_date, end_date)
        
        if not ga4_data:
            return {"synced": 0, "errors": 0}
            
        synced_count = 0
        error_count = 0
        
        # Process each GA4 record
        db = next(get_db())
        try:
            for record in ga4_data:
                try:
                    # Find corresponding UTM link
                    link_id = record.get("link_id")
                    if link_id and link_id.isdigit():
                        utm_link = db.query(UTMLink).filter(UTMLink.id == int(link_id)).first()
                        if utm_link:
                            # Update UTM link with GA4 data
                            utm_link.ga4_clicks = record["event_count"]
                            utm_link.ga4_users = record["total_users"]
                            utm_link.ga4_sessions = record["sessions"]
                            utm_link.ga4_last_sync = datetime.now()
                            
                            synced_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing GA4 record: {e}")
                    error_count += 1
                    
            db.commit()
            logger.info(f"GA4 sync completed: {synced_count} synced, {error_count} errors")
            
        except Exception as e:
            db.rollback()
            logger.error(f"GA4 sync failed: {e}")
            error_count += len(ga4_data)
        finally:
            db.close()
            
        return {"synced": synced_count, "errors": error_count}


# Global GA4 service instance
ga4_service = GA4Service()
