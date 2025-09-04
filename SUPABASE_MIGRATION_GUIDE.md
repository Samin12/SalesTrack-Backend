# 🚀 YouTube Analytics - Supabase Migration Guide

Your YouTube Analytics database has been successfully set up in Supabase! This guide will help you complete the migration and start visualizing your data.

## 📊 What's Been Created

### **Database Tables Created:**
✅ `channels` - YouTube channel information and metrics  
✅ `videos` - Individual video data and performance  
✅ `youtube_data_snapshots` - Daily cached YouTube API data  
✅ `daily_youtube_syncs` - Sync operation tracking  
✅ `channel_metrics` - Historical channel growth data  
✅ `youtube_analytics` - Detailed YouTube Analytics API data  
✅ `weekly_video_metrics` - Weekly performance tracking  
✅ `website_traffic` - Traffic data from YouTube sources  

### **Analytics Views Created:**
✅ `youtube_analytics_dashboard` - Comprehensive analytics overview  
✅ `top_performing_videos` - Videos ranked by performance score  
✅ `weekly_performance_summary` - Weekly aggregated metrics  
✅ `channel_growth_tracking` - Growth metrics with moving averages  

## 🔧 Complete the Migration

### **Step 1: Get Your Supabase Password**
1. Go to your Supabase dashboard: https://supabase.com/dashboard/project/oaxbkmfotoxhizfrmzkx
2. Navigate to **Settings** → **Database**
3. Copy your database password

### **Step 2: Update Configuration**
1. Open `backend/.env` file
2. Replace `[YOUR_SUPABASE_PASSWORD]` with your actual password:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_ACTUAL_PASSWORD@db.oaxbkmfotoxhizfrmzkx.supabase.co:5432/postgres
   ```

### **Step 3: Migrate Your Data**
Run the migration script to transfer your existing SQLite data:
```bash
cd backend
python migrate_to_supabase.py
```

### **Step 4: Restart Your Backend**
```bash
cd backend
uvicorn app.main:app --reload
```

## 📈 Visualize Your Data in Supabase

### **Direct Links to Your Data:**

**🎯 Main Dashboard:**
https://supabase.com/dashboard/project/oaxbkmfotoxhizfrmzkx/editor

**📊 Key Tables for Analytics:**

1. **Videos Performance:**
   https://supabase.com/dashboard/project/oaxbkmfotoxhizfrmzkx/editor/videos

2. **Channel Metrics:**
   https://supabase.com/dashboard/project/oaxbkmfotoxhizfrmzkx/editor/channels

3. **Daily Snapshots:**
   https://supabase.com/dashboard/project/oaxbkmfotoxhizfrmzkx/editor/youtube_data_snapshots

**📈 Analytics Views:**

1. **Top Performing Videos:**
   https://supabase.com/dashboard/project/oaxbkmfotoxhizfrmzkx/editor/top_performing_videos

2. **Weekly Performance Summary:**
   https://supabase.com/dashboard/project/oaxbkmfotoxhizfrmzkx/editor/weekly_performance_summary

3. **Channel Growth Tracking:**
   https://supabase.com/dashboard/project/oaxbkmfotoxhizfrmzkx/editor/channel_growth_tracking

4. **YouTube Analytics Dashboard:**
   https://supabase.com/dashboard/project/oaxbkmfotoxhizfrmzkx/editor/youtube_analytics_dashboard

### **🔍 SQL Editor for Custom Queries:**
https://supabase.com/dashboard/project/oaxbkmfotoxhizfrmzkx/sql

## 📊 Sample Queries for Data Visualization

### **1. Top 10 Videos by Views:**
```sql
SELECT title, view_count, like_count, comment_count, engagement_rate
FROM top_performing_videos
LIMIT 10;
```

### **2. Weekly Growth Trends:**
```sql
SELECT week_start, videos_published, total_views, avg_engagement_rate
FROM weekly_performance_summary
ORDER BY week_start DESC
LIMIT 12;
```

### **3. Channel Growth Over Time:**
```sql
SELECT date, subscriber_count, subscriber_growth, subscriber_growth_rate
FROM channel_growth_tracking
WHERE date >= NOW() - INTERVAL '90 days'
ORDER BY date;
```

### **4. Video Performance by Duration:**
```sql
SELECT 
    CASE 
        WHEN duration_seconds < 300 THEN 'Short (< 5 min)'
        WHEN duration_seconds < 600 THEN 'Medium (5-10 min)'
        ELSE 'Long (> 10 min)'
    END as duration_category,
    COUNT(*) as video_count,
    AVG(view_count) as avg_views,
    AVG(engagement_rate) as avg_engagement
FROM youtube_analytics_dashboard
GROUP BY duration_category;
```

## 🎯 Next Steps

1. **✅ Complete the migration** using the steps above
2. **📊 Explore your data** using the Supabase dashboard
3. **📈 Create custom charts** using the SQL editor
4. **🔄 Set up automated syncing** to keep data fresh
5. **📱 Build custom dashboards** using Supabase's visualization tools

## 🆘 Troubleshooting

**Connection Issues:**
- Verify your Supabase password is correct
- Check that your IP is allowed in Supabase settings
- Ensure the database URL format is correct

**Migration Issues:**
- Make sure SQLite database exists in backend directory
- Check that all required Python packages are installed
- Verify Supabase tables were created successfully

**Data Visualization:**
- Use the SQL editor to test queries before building dashboards
- Check the views for pre-built analytics queries
- Export data to CSV for external visualization tools if needed

## 📞 Support

If you encounter any issues:
1. Check the migration script output for specific error messages
2. Verify your Supabase project is active and accessible
3. Test the database connection using the SQL editor

Your YouTube Analytics data is now ready for powerful visualization in Supabase! 🎉
