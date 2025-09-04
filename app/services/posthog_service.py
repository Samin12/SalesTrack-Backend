"""
PostHog Analytics Integration Service

This service handles:
1. Sending UTM click events to PostHog
2. Fetching analytics data from PostHog API
3. Syncing PostHog data with local database
4. Conversion tracking and user journey analytics
"""

import os
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlencode

import httpx
import requests
from loguru import logger
from posthog import Posthog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.utm_link import UTMLink, LinkClick
from app.core.database import get_db


class PostHogService:
    """PostHog analytics integration service"""
    
    def __init__(self):
        self.api_key = settings.POSTHOG_API_KEY
        self.host = getattr(settings, 'POSTHOG_HOST', 'https://us.posthog.com')
        self.project_id = getattr(settings, 'POSTHOG_PROJECT_ID', None)
        
        # Initialize PostHog client
        if self.api_key:
            try:
                self.client = Posthog(
                    api_key=self.api_key,
                    host=self.host,
                    debug=getattr(settings, 'DEBUG', False)
                )
                logger.info("PostHog client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize PostHog client: {e}")
                self.client = None
        else:
            logger.warning("PostHog API key not configured")
            self.client = None

        # API base URL for PostHog analytics queries
        self.api_base_url = f"{self.host}/api/projects/{self.project_id}" if self.project_id else None

    async def send_utm_click_event(
        self,
        utm_link: UTMLink,
        user_agent: str = None,
        ip_address: str = None,
        referrer: str = None,
        user_id: str = None
    ) -> bool:
        """
        Send UTM click event to PostHog
        
        Args:
            utm_link: UTM link that was clicked
            user_agent: User agent string
            ip_address: Client IP address
            referrer: Referrer URL
            user_id: User identifier (optional)
            
        Returns:
            bool: True if event was sent successfully
        """
        if not self.client:
            logger.warning("PostHog client not initialized")
            return False
            
        try:
            # Generate distinct_id (user identifier)
            distinct_id = user_id or str(uuid.uuid4())
            
            # Prepare event properties
            properties = {
                # UTM parameters
                "utm_source": utm_link.utm_source,
                "utm_medium": utm_link.utm_medium,
                "utm_campaign": utm_link.utm_campaign,
                "utm_content": utm_link.utm_content or "",
                "utm_term": utm_link.utm_term or "",
                
                # Link details
                "link_url": utm_link.destination_url,
                "video_id": utm_link.video_id,
                "link_id": str(utm_link.id),
                "tracking_type": utm_link.tracking_type,
                
                # Context
                "event_category": "UTM Tracking",
                "event_action": "click",
                "event_value": 1,
                
                # Technical details
                "$user_agent": user_agent,
                "$ip": ip_address,
                "$referrer": referrer,
                "$current_url": utm_link.destination_url,
            }
            
            # Remove None values
            properties = {k: v for k, v in properties.items() if v is not None}
            
            # Send event to PostHog
            self.client.capture(
                distinct_id=distinct_id,
                event="utm_link_click",
                properties=properties
            )
            
            logger.info(f"PostHog event sent successfully for UTM link {utm_link.id}")
            return True
                
        except Exception as e:
            logger.error(f"Error sending PostHog event: {e}")
            return False

    async def send_conversion_event(
        self,
        event_type: str,
        event_value: float = 0.0,
        utm_link: UTMLink = None,
        user_id: str = None,
        additional_properties: Dict[str, Any] = None
    ) -> bool:
        """
        Send conversion event to PostHog
        
        Args:
            event_type: Type of conversion (signup, purchase, download, etc.)
            event_value: Monetary value of conversion
            utm_link: Associated UTM link (if any)
            user_id: User identifier
            additional_properties: Additional event properties
            
        Returns:
            bool: True if event was sent successfully
        """
        if not self.client:
            logger.warning("PostHog client not initialized")
            return False
            
        try:
            distinct_id = user_id or str(uuid.uuid4())
            
            properties = {
                "event_type": event_type,
                "event_value": event_value,
                "event_category": "Conversion",
                "event_action": event_type,
            }
            
            # Add UTM context if available
            if utm_link:
                properties.update({
                    "utm_source": utm_link.utm_source,
                    "utm_medium": utm_link.utm_medium,
                    "utm_campaign": utm_link.utm_campaign,
                    "utm_content": utm_link.utm_content or "",
                    "utm_term": utm_link.utm_term or "",
                    "source_video_id": utm_link.video_id,
                    "source_link_id": str(utm_link.id),
                })
            
            # Add additional properties
            if additional_properties:
                properties.update(additional_properties)
            
            # Send conversion event
            self.client.capture(
                distinct_id=distinct_id,
                event=f"conversion_{event_type}",
                properties=properties
            )
            
            logger.info(f"PostHog conversion event sent: {event_type} (value: {event_value})")
            return True
            
        except Exception as e:
            logger.error(f"Error sending PostHog conversion event: {e}")
            return False

    async def fetch_utm_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        utm_source: str = None,
        utm_campaign: str = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch UTM analytics data from PostHog
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            utm_source: Filter by UTM source
            utm_campaign: Filter by UTM campaign
            
        Returns:
            List of analytics data
        """
        if not self.api_key:
            logger.warning("PostHog API key not configured")
            return []
            
        try:
            # PostHog API endpoint for insights
            url = f"{self.host}/api/projects/{self.project_id}/insights/trend/"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Build query parameters
            query_params = {
                "events": [{"id": "utm_link_click", "name": "utm_link_click"}],
                "date_from": start_date.strftime("%Y-%m-%d"),
                "date_to": end_date.strftime("%Y-%m-%d"),
                "breakdown": ["utm_source", "utm_campaign", "link_id", "video_id"],
                "breakdown_type": "event"
            }
            
            # Add filters if specified
            if utm_source or utm_campaign:
                filters = []
                if utm_source:
                    filters.append({
                        "key": "utm_source",
                        "value": utm_source,
                        "operator": "exact"
                    })
                if utm_campaign:
                    filters.append({
                        "key": "utm_campaign", 
                        "value": utm_campaign,
                        "operator": "exact"
                    })
                query_params["properties"] = filters
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=query_params)
                
            if response.status_code == 200:
                data = response.json()
                results = self._process_posthog_analytics_response(data)
                logger.info(f"Fetched {len(results)} PostHog analytics records")
                return results
            else:
                logger.error(f"PostHog API error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching PostHog analytics: {e}")
            return []

    def _process_posthog_analytics_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process PostHog analytics API response"""
        results = []
        
        try:
            # PostHog returns data in a specific format
            # This is a simplified processing - adjust based on actual API response
            if "result" in data:
                for item in data["result"]:
                    if "breakdown_value" in item and "data" in item:
                        breakdown = item["breakdown_value"]
                        event_count = sum(item["data"]) if item["data"] else 0
                        
                        result = {
                            "utm_source": breakdown[0] if len(breakdown) > 0 else "",
                            "utm_campaign": breakdown[1] if len(breakdown) > 1 else "",
                            "link_id": breakdown[2] if len(breakdown) > 2 else "",
                            "video_id": breakdown[3] if len(breakdown) > 3 else "",
                            "event_count": event_count,
                            "total_users": event_count,  # Simplified - would need separate query
                            "sessions": event_count,     # Simplified - would need separate query
                            "date": datetime.now().strftime("%Y-%m-%d")
                        }
                        results.append(result)
                        
        except Exception as e:
            logger.error(f"Error processing PostHog response: {e}")
            
        return results

    async def sync_posthog_data_to_database(self, days_back: int = 7) -> Dict[str, int]:
        """
        Sync PostHog analytics data to local database
        
        Args:
            days_back: Number of days to sync
            
        Returns:
            Dict with sync statistics
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Fetch PostHog data
        posthog_data = await self.fetch_utm_analytics(start_date, end_date)
        
        if not posthog_data:
            return {"synced": 0, "errors": 0}
            
        synced_count = 0
        error_count = 0
        
        # Process each PostHog record
        db = next(get_db())
        try:
            for record in posthog_data:
                try:
                    # Find corresponding UTM link
                    link_id = record.get("link_id")
                    if link_id and link_id.isdigit():
                        utm_link = db.query(UTMLink).filter(UTMLink.id == int(link_id)).first()
                        if utm_link:
                            # Update UTM link with PostHog data
                            utm_link.posthog_events = record["event_count"]
                            utm_link.posthog_users = record["total_users"]
                            utm_link.posthog_sessions = record["sessions"]
                            utm_link.posthog_last_sync = datetime.now()
                            
                            synced_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing PostHog record: {e}")
                    error_count += 1
                    
            db.commit()
            logger.info(f"PostHog sync completed: {synced_count} synced, {error_count} errors")
            
        except Exception as e:
            db.rollback()
            logger.error(f"PostHog sync failed: {e}")
            error_count += len(posthog_data)
        finally:
            db.close()
            
        return {"synced": synced_count, "errors": error_count}

    async def get_website_analytics(self, days: int = 7) -> Dict[str, Any]:
        """
        Fetch website analytics from PostHog for the specified number of days.

        Args:
            days: Number of days to fetch data for (default: 7)

        Returns:
            Dictionary containing website analytics data
        """
        if not self.api_key or not self.project_id:
            logger.warning("PostHog API key or project ID not configured for website analytics")
            return {
                "total_visits": 0,
                "unique_visitors": 0,
                "page_views": 0,
                "daily_visits": [],
                "top_pages": [],
                "error": "PostHog not configured"
            }

        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Get total visits (pageview events)
            async with httpx.AsyncClient() as client:
                # Query for pageview events
                pageview_query = {
                    "events": [{"id": "$pageview", "name": "$pageview"}],
                    "date_from": start_date.strftime("%Y-%m-%d"),
                    "date_to": end_date.strftime("%Y-%m-%d"),
                    "interval": "day"
                }

                response = await client.post(
                    f"{self.api_base_url}/insights/trend/",
                    json=pageview_query,
                    headers=headers,
                    timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()

                    # Extract daily visits
                    daily_visits = []
                    total_visits = 0

                    if data.get("result") and len(data["result"]) > 0:
                        result = data["result"][0]
                        labels = result.get("labels", [])
                        values = result.get("data", [])

                        for i, label in enumerate(labels):
                            visits = values[i] if i < len(values) else 0
                            daily_visits.append({
                                "date": label,
                                "visits": visits
                            })
                            total_visits += visits

                    # Get unique visitors
                    unique_visitors_query = {
                        "events": [{"id": "$pageview", "name": "$pageview"}],
                        "date_from": start_date.strftime("%Y-%m-%d"),
                        "date_to": end_date.strftime("%Y-%m-%d"),
                        "breakdown": "distinct_id",
                        "breakdown_type": "person"
                    }

                    unique_response = await client.post(
                        f"{self.api_base_url}/insights/trend/",
                        json=unique_visitors_query,
                        headers=headers,
                        timeout=30.0
                    )

                    unique_visitors = 0
                    if unique_response.status_code == 200:
                        unique_data = unique_response.json()
                        if unique_data.get("result"):
                            unique_visitors = len(unique_data["result"])

                    # Get top pages
                    top_pages_query = {
                        "events": [{"id": "$pageview", "name": "$pageview"}],
                        "date_from": start_date.strftime("%Y-%m-%d"),
                        "date_to": end_date.strftime("%Y-%m-%d"),
                        "breakdown": "$current_url",
                        "breakdown_type": "event"
                    }

                    pages_response = await client.post(
                        f"{self.api_base_url}/insights/trend/",
                        json=top_pages_query,
                        headers=headers,
                        timeout=30.0
                    )

                    top_pages = []
                    if pages_response.status_code == 200:
                        pages_data = pages_response.json()
                        if pages_data.get("result"):
                            for page_result in pages_data["result"][:10]:  # Top 10 pages
                                page_url = page_result.get("breakdown_value", "Unknown")
                                page_views = sum(page_result.get("data", []))
                                if page_views > 0:
                                    top_pages.append({
                                        "url": page_url,
                                        "views": page_views
                                    })

                    return {
                        "total_visits": total_visits,
                        "unique_visitors": unique_visitors,
                        "page_views": total_visits,  # For now, same as visits
                        "daily_visits": daily_visits,
                        "top_pages": sorted(top_pages, key=lambda x: x["views"], reverse=True),
                        "period_days": days,
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d")
                    }
                else:
                    logger.error(f"PostHog API error: {response.status_code} - {response.text}")
                    return {
                        "total_visits": 0,
                        "unique_visitors": 0,
                        "page_views": 0,
                        "daily_visits": [],
                        "top_pages": [],
                        "error": f"API error: {response.status_code}"
                    }

        except Exception as e:
            logger.error(f"Error fetching website analytics from PostHog: {e}")
            return {
                "total_visits": 0,
                "unique_visitors": 0,
                "page_views": 0,
                "daily_visits": [],
                "top_pages": [],
                "error": str(e)
            }

    def __del__(self):
        """Cleanup PostHog client on destruction"""
        if hasattr(self, 'client') and self.client:
            try:
                self.client.shutdown()
            except:
                pass


# Global PostHog service instance
posthog_service = PostHogService()
