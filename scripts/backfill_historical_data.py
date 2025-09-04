#!/usr/bin/env python3
"""
Script to backfill historical data for better chart visualization.
This creates sample historical data points for the last 30 days.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.channel import ChannelMetrics
from app.models.video import VideoMetrics, Video
from app.core.config import get_youtube_config
import random


def backfill_channel_metrics(db: Session, channel_id: str, days: int = 30):
    """Create sample historical channel metrics for the last N days."""
    
    # Get current metrics as baseline
    current_metrics = db.query(ChannelMetrics).filter(
        ChannelMetrics.channel_id == channel_id
    ).order_by(ChannelMetrics.date.desc()).first()
    
    if not current_metrics:
        print("No current metrics found. Run comprehensive tracking initialization first.")
        return
    
    print(f"Backfilling {days} days of historical data...")
    
    # Current values
    current_subs = current_metrics.subscriber_count
    current_views = current_metrics.view_count
    
    # Generate historical data points
    for i in range(days, 0, -1):  # Go backwards from days ago to yesterday
        date = datetime.now(timezone.utc) - timedelta(days=i)
        
        # Calculate historical values (simulate gradual growth)
        # Assume roughly 1-3% growth over the period
        growth_factor = 1 - (i * 0.001)  # Small daily growth
        historical_subs = int(current_subs * growth_factor)
        historical_views = int(current_views * growth_factor)
        
        # Add some randomness for realistic variation
        daily_sub_change = random.randint(-5, 15)  # Daily subscriber change
        daily_view_change = random.randint(50, 500)  # Daily view change
        
        historical_subs += daily_sub_change * (days - i)
        historical_views += daily_view_change * (days - i)
        
        # Ensure values don't go negative or exceed current
        historical_subs = max(historical_subs, current_subs - 1000)
        historical_subs = min(historical_subs, current_subs)
        historical_views = max(historical_views, current_views - 10000)
        historical_views = min(historical_views, current_views)
        
        # Calculate growth from previous day
        prev_date = date - timedelta(days=1)
        prev_metrics = db.query(ChannelMetrics).filter(
            ChannelMetrics.channel_id == channel_id,
            ChannelMetrics.date >= prev_date,
            ChannelMetrics.date < prev_date + timedelta(days=1)
        ).first()
        
        if prev_metrics:
            sub_growth = historical_subs - prev_metrics.subscriber_count
            view_growth = historical_views - prev_metrics.view_count
            
            sub_growth_rate = (sub_growth / prev_metrics.subscriber_count * 100) if prev_metrics.subscriber_count > 0 else 0
            view_growth_rate = (view_growth / prev_metrics.view_count * 100) if prev_metrics.view_count > 0 else 0
        else:
            sub_growth = 0
            view_growth = 0
            sub_growth_rate = 0.0
            view_growth_rate = 0.0
        
        # Check if metrics for this date already exist
        existing = db.query(ChannelMetrics).filter(
            ChannelMetrics.channel_id == channel_id,
            ChannelMetrics.date >= date,
            ChannelMetrics.date < date + timedelta(days=1)
        ).first()
        
        if not existing:
            metrics = ChannelMetrics(
                channel_id=channel_id,
                date=date,
                subscriber_count=historical_subs,
                view_count=historical_views,
                video_count=current_metrics.video_count,  # Assume video count was same
                subscriber_growth=sub_growth,
                subscriber_growth_rate=sub_growth_rate,
                view_growth=view_growth,
                view_growth_rate=view_growth_rate,
                data_source="backfill_simulation"
            )
            db.add(metrics)
            print(f"Added metrics for {date.date()}: {historical_subs} subs, {historical_views} views")
    
    db.commit()
    print(f"Backfilled {days} days of channel metrics")


def backfill_video_metrics(db: Session, channel_id: str, days: int = 30):
    """Create sample historical video metrics for top videos."""
    
    # Get top 10 videos by view count
    top_videos = db.query(Video).filter(
        Video.channel_id == channel_id
    ).order_by(Video.view_count.desc()).limit(10).all()
    
    print(f"Backfilling video metrics for {len(top_videos)} top videos...")
    
    for video in top_videos:
        current_views = video.view_count
        current_likes = video.like_count
        current_comments = video.comment_count
        
        for i in range(days, 0, -1):
            date = datetime.now(timezone.utc) - timedelta(days=i)
            
            # Calculate historical values
            growth_factor = 1 - (i * 0.002)  # Slightly higher growth for individual videos
            historical_views = int(current_views * growth_factor)
            historical_likes = int(current_likes * growth_factor)
            historical_comments = int(current_comments * growth_factor)
            
            # Add daily variation
            daily_view_change = random.randint(1, 50)
            daily_like_change = random.randint(0, 5)
            daily_comment_change = random.randint(0, 2)
            
            historical_views += daily_view_change * (days - i)
            historical_likes += daily_like_change * (days - i)
            historical_comments += daily_comment_change * (days - i)
            
            # Ensure values don't exceed current
            historical_views = min(historical_views, current_views)
            historical_likes = min(historical_likes, current_likes)
            historical_comments = min(historical_comments, current_comments)
            
            # Calculate growth rates
            prev_date = date - timedelta(days=1)
            prev_metrics = db.query(VideoMetrics).filter(
                VideoMetrics.video_id == video.video_id,
                VideoMetrics.date >= prev_date,
                VideoMetrics.date < prev_date + timedelta(days=1)
            ).first()
            
            if prev_metrics:
                view_growth = historical_views - prev_metrics.view_count
                view_growth_rate = (view_growth / prev_metrics.view_count * 100) if prev_metrics.view_count > 0 else 0
            else:
                view_growth = 0
                view_growth_rate = 0.0
            
            # Check if metrics already exist
            existing = db.query(VideoMetrics).filter(
                VideoMetrics.video_id == video.video_id,
                VideoMetrics.date >= date,
                VideoMetrics.date < date + timedelta(days=1)
            ).first()
            
            if not existing:
                # Calculate engagement rates
                like_rate = historical_likes / historical_views if historical_views > 0 else 0
                comment_rate = historical_comments / historical_views if historical_views > 0 else 0
                engagement_rate = (historical_likes + historical_comments) / historical_views if historical_views > 0 else 0
                
                metrics = VideoMetrics(
                    video_id=video.video_id,
                    date=date,
                    view_count=historical_views,
                    like_count=historical_likes,
                    comment_count=historical_comments,
                    view_growth=view_growth,
                    view_growth_rate=view_growth_rate,
                    like_rate=like_rate,
                    comment_rate=comment_rate,
                    engagement_rate=engagement_rate,
                    data_source="backfill_simulation"
                )
                db.add(metrics)
    
    db.commit()
    print(f"Backfilled video metrics for {len(top_videos)} videos over {days} days")


def main():
    """Main function to run the backfill process."""
    print("Starting historical data backfill...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get channel ID
        youtube_config = get_youtube_config()
        channel_id = youtube_config.get("channel_id")
        
        print(f"Backfilling data for channel: {channel_id}")
        
        # Backfill channel metrics
        backfill_channel_metrics(db, channel_id, days=30)
        
        # Backfill video metrics
        backfill_video_metrics(db, channel_id, days=30)
        
        print("Historical data backfill completed successfully!")
        print("Growth charts should now display meaningful data.")
        
    except Exception as e:
        print(f"Error during backfill: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
