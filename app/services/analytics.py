"""
Analytics processing service for calculating growth metrics and insights.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from loguru import logger
import pandas as pd

from app.models.channel import Channel, ChannelMetrics
from app.models.video import Video, VideoMetrics
from app.models.traffic import WebsiteTraffic, ConversionEvent
from app.models.utm_link import UTMLink, LinkClick
from app.services.posthog_service import posthog_service


class AnalyticsProcessor:
    """Service for processing and analyzing YouTube analytics data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_channel_growth(self, channel_id: str, days: int = 7) -> Dict[str, Any]:
        """Calculate week-over-week channel growth metrics."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            previous_start = start_date - timedelta(days=days)
            
            # Get current period metrics
            current_metrics = self.db.query(ChannelMetrics).filter(
                ChannelMetrics.channel_id == channel_id,
                ChannelMetrics.date >= start_date,
                ChannelMetrics.date <= end_date
            ).order_by(desc(ChannelMetrics.date)).first()
            
            # Get previous period metrics
            previous_metrics = self.db.query(ChannelMetrics).filter(
                ChannelMetrics.channel_id == channel_id,
                ChannelMetrics.date >= previous_start,
                ChannelMetrics.date < start_date
            ).order_by(desc(ChannelMetrics.date)).first()
            
            if not current_metrics or not previous_metrics:
                return {"error": "Insufficient data for growth calculation"}
            
            # Calculate growth metrics
            subscriber_growth = current_metrics.subscriber_count - previous_metrics.subscriber_count
            subscriber_growth_rate = (
                (subscriber_growth / previous_metrics.subscriber_count * 100) 
                if previous_metrics.subscriber_count > 0 else 0
            )
            
            view_growth = current_metrics.view_count - previous_metrics.view_count
            view_growth_rate = (
                (view_growth / previous_metrics.view_count * 100) 
                if previous_metrics.view_count > 0 else 0
            )
            
            return {
                "period_days": days,
                "current_subscribers": current_metrics.subscriber_count,
                "previous_subscribers": previous_metrics.subscriber_count,
                "subscriber_growth": subscriber_growth,
                "subscriber_growth_rate": subscriber_growth_rate,
                "current_views": current_metrics.view_count,
                "previous_views": previous_metrics.view_count,
                "view_growth": view_growth,
                "view_growth_rate": view_growth_rate,
                "growth_trend": "positive" if subscriber_growth > 0 else "negative" if subscriber_growth < 0 else "stable"
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate channel growth: {e}")
            return {"error": str(e)}
    
    def identify_fastest_growing_videos(self, channel_id: str, days: int = 30, limit: int = 10) -> List[Dict[str, Any]]:
        """Identify fastest-growing videos based on recent performance."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get videos with recent metrics
            video_growth_query = self.db.query(
                Video.video_id,
                Video.title,
                Video.published_at,
                Video.view_count.label('current_views'),
                func.max(VideoMetrics.view_growth_rate).label('max_growth_rate'),
                func.sum(VideoMetrics.view_growth).label('total_growth')
            ).join(
                VideoMetrics, Video.video_id == VideoMetrics.video_id
            ).filter(
                Video.channel_id == channel_id,
                VideoMetrics.date >= start_date,
                VideoMetrics.date <= end_date
            ).group_by(
                Video.video_id, Video.title, Video.published_at, Video.view_count
            ).order_by(desc('max_growth_rate')).limit(limit)
            
            results = video_growth_query.all()
            
            fastest_growing = []
            for result in results:
                video_data = {
                    "video_id": result.video_id,
                    "title": result.title,
                    "published_at": result.published_at.isoformat(),
                    "current_views": result.current_views,
                    "max_growth_rate": float(result.max_growth_rate or 0),
                    "total_growth": int(result.total_growth or 0),
                    "growth_category": self._categorize_growth_rate(result.max_growth_rate or 0)
                }
                fastest_growing.append(video_data)
            
            return fastest_growing
            
        except Exception as e:
            logger.error(f"Failed to identify fastest growing videos: {e}")
            return []
    
    def calculate_video_performance_trends(self, video_id: str, days: int = 30) -> Dict[str, Any]:
        """Calculate performance trends for a specific video."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get video metrics over time
            metrics = self.db.query(VideoMetrics).filter(
                VideoMetrics.video_id == video_id,
                VideoMetrics.date >= start_date,
                VideoMetrics.date <= end_date
            ).order_by(VideoMetrics.date).all()
            
            if len(metrics) < 2:
                return {"error": "Insufficient data for trend analysis"}
            
            # Convert to pandas for easier analysis
            df = pd.DataFrame([
                {
                    "date": m.date,
                    "views": m.view_count,
                    "likes": m.like_count,
                    "comments": m.comment_count,
                    "engagement_rate": m.engagement_rate
                }
                for m in metrics
            ])
            
            # Calculate trends
            view_trend = self._calculate_trend(df['views'].tolist())
            engagement_trend = self._calculate_trend(df['engagement_rate'].tolist())
            
            # Calculate velocity (rate of change)
            days_diff = (df['date'].iloc[-1] - df['date'].iloc[0]).days or 1
            view_velocity = (df['views'].iloc[-1] - df['views'].iloc[0]) / days_diff
            
            # Identify peak performance day
            peak_day_idx = df['views'].idxmax()
            peak_day = df.iloc[peak_day_idx]
            
            return {
                "analysis_period_days": days,
                "total_data_points": len(metrics),
                "view_trend": view_trend,
                "engagement_trend": engagement_trend,
                "average_daily_view_growth": view_velocity,
                "peak_performance_date": peak_day['date'].isoformat(),
                "peak_views": int(peak_day['views']),
                "current_momentum": self._assess_momentum(df['views'].tail(7).tolist()),
                "performance_category": self._categorize_performance(view_velocity, df['engagement_rate'].mean())
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate video performance trends: {e}")
            return {"error": str(e)}
    
    def analyze_traffic_conversion(self, days: int = 30) -> Dict[str, Any]:
        """Analyze website traffic conversion from YouTube sources."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get traffic data
            traffic_data = self.db.query(WebsiteTraffic).filter(
                WebsiteTraffic.date >= start_date,
                WebsiteTraffic.date <= end_date
            ).all()
            
            # Get conversion events
            conversion_data = self.db.query(ConversionEvent).filter(
                ConversionEvent.date >= start_date,
                ConversionEvent.date <= end_date,
                ConversionEvent.youtube_source.isnot(None)
            ).all()
            
            if not traffic_data:
                return {"error": "No traffic data available"}
            
            # Calculate conversion metrics
            total_clicks = sum(t.clicks for t in traffic_data)
            total_page_views = sum(t.page_views for t in traffic_data)
            total_conversions = len(conversion_data)
            total_conversion_value = sum(c.event_value for c in conversion_data)
            
            # Calculate rates
            click_to_page_rate = (total_page_views / total_clicks * 100) if total_clicks > 0 else 0
            conversion_rate = (total_conversions / total_page_views * 100) if total_page_views > 0 else 0
            
            # Analyze by source
            source_analysis = {}
            for traffic in traffic_data:
                source = traffic.source
                if source not in source_analysis:
                    source_analysis[source] = {
                        "clicks": 0,
                        "page_views": 0,
                        "conversions": 0,
                        "conversion_value": 0
                    }
                
                source_analysis[source]["clicks"] += traffic.clicks
                source_analysis[source]["page_views"] += traffic.page_views
            
            # Add conversion data to source analysis
            for conversion in conversion_data:
                source = conversion.youtube_source
                if source in source_analysis:
                    source_analysis[source]["conversions"] += 1
                    source_analysis[source]["conversion_value"] += conversion.event_value
            
            # Calculate source-specific rates
            for source, data in source_analysis.items():
                data["click_to_page_rate"] = (data["page_views"] / data["clicks"] * 100) if data["clicks"] > 0 else 0
                data["conversion_rate"] = (data["conversions"] / data["page_views"] * 100) if data["page_views"] > 0 else 0
                data["value_per_click"] = data["conversion_value"] / data["clicks"] if data["clicks"] > 0 else 0
            
            return {
                "analysis_period_days": days,
                "total_clicks": total_clicks,
                "total_page_views": total_page_views,
                "total_conversions": total_conversions,
                "total_conversion_value": total_conversion_value,
                "click_to_page_rate": click_to_page_rate,
                "conversion_rate": conversion_rate,
                "average_conversion_value": total_conversion_value / total_conversions if total_conversions > 0 else 0,
                "source_breakdown": source_analysis,
                "top_converting_source": max(source_analysis.items(), key=lambda x: x[1]["conversion_rate"])[0] if source_analysis else None
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze traffic conversion: {e}")
            return {"error": str(e)}
    
    def generate_insights(self, channel_id: str) -> List[str]:
        """Generate actionable insights based on analytics data."""
        insights = []
        
        try:
            # Channel growth insights
            growth_data = self.calculate_channel_growth(channel_id, days=7)
            if "error" not in growth_data:
                if growth_data["subscriber_growth_rate"] > 5:
                    insights.append(f"Strong subscriber growth: {growth_data['subscriber_growth_rate']:.1f}% this week")
                elif growth_data["subscriber_growth_rate"] < -2:
                    insights.append(f"Subscriber decline detected: {growth_data['subscriber_growth_rate']:.1f}% this week")
                
                if growth_data["view_growth_rate"] > 10:
                    insights.append("Excellent view growth momentum - consider increasing upload frequency")
            
            # Video performance insights
            fastest_growing = self.identify_fastest_growing_videos(channel_id, days=30, limit=3)
            if fastest_growing:
                top_video = fastest_growing[0]
                insights.append(f"Top performing video: '{top_video['title'][:50]}...' with {top_video['max_growth_rate']:.1f}% growth rate")
            
            # Traffic conversion insights
            conversion_data = self.analyze_traffic_conversion(days=30)
            if "error" not in conversion_data and conversion_data["conversion_rate"] > 0:
                insights.append(f"YouTube traffic converting at {conversion_data['conversion_rate']:.1f}% rate")
                
                if conversion_data["top_converting_source"]:
                    insights.append(f"Best converting source: {conversion_data['top_converting_source']}")
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return ["Unable to generate insights due to data processing error"]
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values."""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear trend calculation
        n = len(values)
        x = list(range(n))
        
        # Calculate slope
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return "stable"
        
        slope = numerator / denominator
        
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"
    
    def _categorize_growth_rate(self, growth_rate: float) -> str:
        """Categorize growth rate into performance buckets."""
        if growth_rate >= 20:
            return "viral"
        elif growth_rate >= 10:
            return "high_growth"
        elif growth_rate >= 5:
            return "moderate_growth"
        elif growth_rate >= 0:
            return "slow_growth"
        else:
            return "declining"
    
    def _assess_momentum(self, recent_values: List[float]) -> str:
        """Assess current momentum based on recent values."""
        if len(recent_values) < 3:
            return "unknown"
        
        trend = self._calculate_trend(recent_values)
        
        if trend == "increasing":
            return "accelerating"
        elif trend == "decreasing":
            return "decelerating"
        else:
            return "stable"
    
    def _categorize_performance(self, view_velocity: float, avg_engagement: float) -> str:
        """Categorize overall video performance."""
        if view_velocity > 1000 and avg_engagement > 5:
            return "excellent"
        elif view_velocity > 500 and avg_engagement > 3:
            return "good"
        elif view_velocity > 100 and avg_engagement > 1:
            return "average"
        else:
            return "needs_improvement"

    async def analyze_posthog_utm_performance(self, days: int = 30) -> Dict[str, Any]:
        """Analyze UTM link performance using PostHog data."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Get UTM links with PostHog data
            utm_links = self.db.query(UTMLink).filter(
                UTMLink.posthog_enabled == True,
                UTMLink.created_at >= start_date
            ).all()

            if not utm_links:
                return {"error": "No PostHog-enabled UTM links found"}

            # Fetch fresh PostHog analytics data
            posthog_data = await posthog_service.fetch_utm_analytics(start_date, end_date)

            # Combine local and PostHog data
            performance_data = []
            for link in utm_links:
                # Find corresponding PostHog data
                posthog_metrics = next(
                    (item for item in posthog_data if item.get("link_id") == str(link.id)),
                    {}
                )

                # Get local click data
                local_clicks = self.db.query(LinkClick).filter(
                    LinkClick.utm_link_id == link.id,
                    LinkClick.clicked_at >= start_date
                ).count()

                performance_data.append({
                    "link_id": link.id,
                    "video_id": link.video_id,
                    "utm_campaign": link.utm_campaign,
                    "utm_source": link.utm_source,
                    "utm_medium": link.utm_medium,
                    "local_clicks": local_clicks,
                    "posthog_events": posthog_metrics.get("event_count", 0),
                    "posthog_users": posthog_metrics.get("total_users", 0),
                    "posthog_sessions": posthog_metrics.get("sessions", 0),
                    "created_at": link.created_at.isoformat()
                })

            # Calculate summary metrics
            total_local_clicks = sum(item["local_clicks"] for item in performance_data)
            total_posthog_events = sum(item["posthog_events"] for item in performance_data)
            total_posthog_users = sum(item["posthog_users"] for item in performance_data)

            # Find top performing campaigns
            campaign_performance = {}
            for item in performance_data:
                campaign = item["utm_campaign"]
                if campaign not in campaign_performance:
                    campaign_performance[campaign] = {
                        "local_clicks": 0,
                        "posthog_events": 0,
                        "posthog_users": 0
                    }
                campaign_performance[campaign]["local_clicks"] += item["local_clicks"]
                campaign_performance[campaign]["posthog_events"] += item["posthog_events"]
                campaign_performance[campaign]["posthog_users"] += item["posthog_users"]

            # Sort campaigns by performance
            top_campaigns = sorted(
                campaign_performance.items(),
                key=lambda x: x[1]["posthog_events"],
                reverse=True
            )[:5]

            return {
                "analysis_period_days": days,
                "total_utm_links": len(utm_links),
                "total_local_clicks": total_local_clicks,
                "total_posthog_events": total_posthog_events,
                "total_posthog_users": total_posthog_users,
                "average_events_per_link": total_posthog_events / len(utm_links) if utm_links else 0,
                "top_campaigns": [{"campaign": camp[0], **camp[1]} for camp in top_campaigns],
                "link_performance": performance_data
            }

        except Exception as e:
            logger.error(f"Failed to analyze PostHog UTM performance: {e}")
            return {"error": str(e)}
