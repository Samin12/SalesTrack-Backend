"""
UTM Link tracking service for video-driven traffic analytics.
"""
import uuid
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode, urlparse, parse_qs
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.models.utm_link import UTMLink, LinkClick
from app.models.video import Video
from app.core.database import get_db


class UTMService:
    """Service for managing UTM tracking links and analytics."""
    
    def __init__(self, db: Session):
        self.db = db

    def _generate_pretty_slug(self, destination_url: str, video_id: str) -> str:
        """Generate a pretty slug from destination URL and video ID."""
        try:
            parsed = urlparse(destination_url)
            domain = parsed.netloc.replace('www.', '')
            path = parsed.path.strip('/')

            # Extract meaningful parts
            domain_parts = domain.split('.')
            if len(domain_parts) > 1:
                domain_name = domain_parts[0]  # e.g., 'skool' from 'skool.com'
            else:
                domain_name = domain

            # Clean up path
            if path:
                path_clean = re.sub(r'[^a-zA-Z0-9-]', '-', path)
                path_clean = re.sub(r'-+', '-', path_clean).strip('-')
                slug = f"{domain_name}-{path_clean}"
            else:
                slug = domain_name

            # Add video ID suffix to ensure uniqueness (shorter)
            video_suffix = video_id[:6] if len(video_id) > 6 else video_id
            slug = f"{slug}-{video_suffix}"

            # Ensure slug is not too long (shorter limit for better URLs)
            if len(slug) > 50:
                slug = slug[:50]

            return slug.lower()
        except Exception:
            # Fallback to simple slug
            return f"link-{video_id}"

    def _ensure_unique_slug(self, base_slug: str) -> str:
        """Ensure the slug is unique by adding a counter if needed."""
        slug = base_slug
        counter = 1

        while True:
            existing = self.db.query(UTMLink).filter(UTMLink.pretty_slug == slug).first()
            if not existing:
                return slug
            counter += 1
            slug = f"{base_slug}-{counter}"
    
    def create_utm_link(
        self,
        video_id: str,
        destination_url: str,
        utm_content: Optional[str] = None,
        utm_term: Optional[str] = None,
        tracking_type: str = "server_redirect"
    ) -> UTMLink:
        """Create a new UTM tracking link for a video."""

        # Note: We don't require the video to exist in our database yet
        # This allows tracking links for new videos that haven't been uploaded/synced
        # The video will be added to our database when the next sync occurs

        # Generate UTM parameters
        utm_campaign = f"video_{video_id}"
        
        # Build UTM parameters
        utm_params = {
            'utm_source': 'youtube',
            'utm_medium': 'video',
            'utm_campaign': utm_campaign,
        }
        
        if utm_content:
            utm_params['utm_content'] = utm_content
        if utm_term:
            utm_params['utm_term'] = utm_term
        
        # Generate tracking URL (always generated for backward compatibility)
        tracking_url = self._build_tracking_url(destination_url, utm_params)

        # Generate direct URL for PostHog/GA4-only tracking
        # For direct PostHog/GA4, this should always be the destination URL with UTM parameters
        direct_url = tracking_url if tracking_type in ["direct_posthog", "direct_ga4"] else None

        # Generate pretty slug for both tracking types (for short URLs)
        base_slug = self._generate_pretty_slug(destination_url, video_id)
        pretty_slug = self._ensure_unique_slug(base_slug)

        # Create UTM link record
        utm_link = UTMLink(
            video_id=video_id,
            destination_url=destination_url,
            utm_source=utm_params['utm_source'],
            utm_medium=utm_params['utm_medium'],
            utm_campaign=utm_params['utm_campaign'],
            utm_content=utm_content,
            utm_term=utm_term,
            tracking_url=tracking_url,
            pretty_slug=pretty_slug,
            tracking_type=tracking_type,
            direct_url=direct_url
        )
        
        self.db.add(utm_link)
        self.db.commit()
        self.db.refresh(utm_link)
        
        return utm_link
    
    def _build_tracking_url(self, destination_url: str, utm_params: Dict[str, str]) -> str:
        """Build the complete tracking URL with UTM parameters."""
        parsed_url = urlparse(destination_url)
        existing_params = parse_qs(parsed_url.query)
        
        # Convert existing params to single values
        for key, value_list in existing_params.items():
            existing_params[key] = value_list[0] if value_list else ''
        
        # Add UTM parameters
        all_params = {**existing_params, **utm_params}
        
        # Build final URL
        query_string = urlencode(all_params)
        
        if parsed_url.netloc:
            # Full URL
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        else:
            # Relative URL
            base_url = parsed_url.path
        
        return f"{base_url}?{query_string}"
    
    def record_click(
        self,
        utm_link_id: int,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> LinkClick:
        """Record a click event for a UTM link."""
        
        click = LinkClick(
            utm_link_id=utm_link_id,
            user_agent=user_agent,
            ip_address=ip_address,
            referrer=referrer
        )
        
        self.db.add(click)
        self.db.commit()
        self.db.refresh(click)
        
        return click
    
    def get_utm_links(
        self,
        video_id: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[UTMLink]:
        """Get UTM links with optional filtering."""
        
        query = self.db.query(UTMLink)
        
        if video_id:
            query = query.filter(UTMLink.video_id == video_id)
        
        if active_only:
            query = query.filter(UTMLink.is_active == 1)
        
        query = query.order_by(desc(UTMLink.created_at))
        query = query.offset(offset).limit(limit)
        
        return query.all()

    def get_utm_links_with_stats(
        self,
        video_id: Optional[str] = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get UTM links with click statistics."""

        # Build base query with click count subquery
        click_count_subquery = (
            self.db.query(
                LinkClick.utm_link_id,
                func.count(LinkClick.id).label('click_count'),
                func.max(LinkClick.clicked_at).label('last_clicked')
            )
            .group_by(LinkClick.utm_link_id)
            .subquery()
        )

        # Main query joining UTM links with click statistics
        query = (
            self.db.query(
                UTMLink,
                func.coalesce(click_count_subquery.c.click_count, 0).label('click_count'),
                click_count_subquery.c.last_clicked
            )
            .outerjoin(click_count_subquery, UTMLink.id == click_count_subquery.c.utm_link_id)
        )

        if video_id:
            query = query.filter(UTMLink.video_id == video_id)

        if active_only:
            query = query.filter(UTMLink.is_active == 1)

        query = query.order_by(desc(UTMLink.created_at))
        query = query.offset(offset).limit(limit)

        # Convert results to dictionaries with click statistics
        results = []
        for utm_link, click_count, last_clicked in query.all():
            link_dict = {
                'id': utm_link.id,
                'video_id': utm_link.video_id,
                'destination_url': utm_link.destination_url,
                'utm_source': utm_link.utm_source,
                'utm_medium': utm_link.utm_medium,
                'utm_campaign': utm_link.utm_campaign,
                'utm_content': utm_link.utm_content,
                'utm_term': utm_link.utm_term,
                'tracking_url': utm_link.tracking_url,
                'pretty_slug': utm_link.pretty_slug,
                'tracking_type': utm_link.tracking_type,
                'direct_url': utm_link.direct_url,
                'shareable_url': utm_link.shareable_url,
                'created_at': utm_link.created_at,
                'is_active': utm_link.is_active,
                'click_count': int(click_count) if click_count else 0,
                'last_clicked': last_clicked
            }
            results.append(link_dict)

        return results

    def get_link_analytics(
        self,
        utm_link_id: int,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """Get analytics data for a specific UTM link."""
        
        utm_link = self.db.query(UTMLink).filter(UTMLink.id == utm_link_id).first()
        if not utm_link:
            raise ValueError(f"UTM link with ID {utm_link_id} not found")
        
        # Date range for analytics
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Total clicks
        total_clicks = self.db.query(func.count(LinkClick.id)).filter(
            LinkClick.utm_link_id == utm_link_id
        ).scalar()
        
        # Clicks in date range
        recent_clicks = self.db.query(func.count(LinkClick.id)).filter(
            and_(
                LinkClick.utm_link_id == utm_link_id,
                LinkClick.clicked_at >= start_date
            )
        ).scalar()
        
        # Daily click data
        daily_clicks = self.db.query(
            func.date(LinkClick.clicked_at).label('date'),
            func.count(LinkClick.id).label('clicks')
        ).filter(
            and_(
                LinkClick.utm_link_id == utm_link_id,
                LinkClick.clicked_at >= start_date
            )
        ).group_by(func.date(LinkClick.clicked_at)).all()
        
        return {
            'utm_link_id': utm_link_id,
            'video_id': utm_link.video_id,
            'destination_url': utm_link.destination_url,
            'tracking_url': utm_link.tracking_url,
            'total_clicks': total_clicks or 0,
            'recent_clicks': recent_clicks or 0,
            'daily_clicks': [
                {'date': str(day.date), 'clicks': day.clicks}
                for day in daily_clicks
            ],
            'created_at': utm_link.created_at,
            'is_active': utm_link.is_active
        }
    
    def get_video_link_performance(self, video_id: str) -> Dict[str, Any]:
        """Get link performance data for a specific video."""
        
        video = self.db.query(Video).filter(Video.video_id == video_id).first()
        if not video:
            raise ValueError(f"Video with ID {video_id} not found")
        
        # Get all UTM links for this video
        utm_links = self.db.query(UTMLink).filter(
            UTMLink.video_id == video_id
        ).all()
        
        # Calculate total clicks across all links
        total_clicks = self.db.query(func.count(LinkClick.id)).join(
            UTMLink, LinkClick.utm_link_id == UTMLink.id
        ).filter(UTMLink.video_id == video_id).scalar()
        
        # Calculate CTR (clicks / views)
        ctr = 0.0
        if video.view_count and video.view_count > 0:
            ctr = (total_clicks / video.view_count) * 100
        
        return {
            'video_id': video_id,
            'video_title': video.title,
            'video_views': video.view_count or 0,
            'total_links': len(utm_links),
            'total_clicks': total_clicks or 0,
            'click_through_rate': round(ctr, 2),
            'views_to_clicks_ratio': f"1:{int(video.view_count / max(total_clicks, 1))}" if video.view_count else "N/A",
            'links': [
                {
                    'id': link.id,
                    'destination_url': link.destination_url,
                    'tracking_url': link.tracking_url,
                    'clicks': len(link.clicks),
                    'created_at': link.created_at
                }
                for link in utm_links
            ]
        }
    
    def get_video_traffic_correlation(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get correlation data between video views and link clicks."""

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        # First, get all videos that have UTM links using the same approach as get_utm_links_with_stats
        utm_links_with_stats = self.get_utm_links_with_stats(active_only=True, limit=1000)

        # Group by video_id to aggregate data
        video_data = {}
        for link in utm_links_with_stats:
            video_id = link['video_id']
            if video_id not in video_data:
                # Get video info from database
                video = self.db.query(Video).filter(Video.video_id == video_id).first()
                video_data[video_id] = {
                    'video_id': video_id,
                    'video_title': video.title if video else f"Video {video_id}",
                    'publication_date': video.published_at.isoformat() if video and video.published_at else datetime.utcnow().isoformat(),
                    'video_views': video.view_count if video else 0,
                    'link_count': 0,
                    'total_clicks': 0
                }

            video_data[video_id]['link_count'] += 1
            video_data[video_id]['total_clicks'] += link['click_count']

        # Convert to list and calculate additional metrics
        correlation_data = []
        for video_info in video_data.values():
            ctr = 0.0
            if video_info['video_views'] and video_info['video_views'] > 0:
                ctr = (video_info['total_clicks'] / video_info['video_views']) * 100

            correlation_data.append({
                'video_id': video_info['video_id'],
                'video_title': video_info['video_title'],
                'publication_date': video_info['publication_date'],
                'video_views': video_info['video_views'],
                'link_count': video_info['link_count'],
                'total_clicks': video_info['total_clicks'],
                'click_through_rate': round(ctr, 4),
                'views_to_clicks_ratio': f"1:{int(video_info['video_views'] / max(video_info['total_clicks'], 1))}" if video_info['video_views'] else "N/A"
            })

        # Sort by video views descending
        correlation_data.sort(key=lambda x: x['video_views'], reverse=True)

        return correlation_data

    def delete_utm_link(self, link_id: int) -> bool:
        """Delete a UTM tracking link and its associated clicks."""
        try:
            # Get the UTM link
            utm_link = self.db.query(UTMLink).filter(UTMLink.id == link_id).first()

            if not utm_link:
                return False

            # Delete associated clicks first (due to foreign key constraint)
            self.db.query(LinkClick).filter(LinkClick.utm_link_id == link_id).delete()

            # Delete the UTM link
            self.db.delete(utm_link)
            self.db.commit()

            return True

        except Exception as e:
            self.db.rollback()
            raise e
