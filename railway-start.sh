#!/bin/bash

# Railway startup script for FastAPI backend

echo "Starting YouTube Analytics Backend on Railway..."

# Set environment variables for production
export ENVIRONMENT=production
export DEBUG=false
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

# Create database tables if they don't exist
echo "Initializing database..."
python3 -c "
try:
    from app.core.database import create_tables
    create_tables()
    print('Database tables created successfully')
except Exception as e:
    print(f'Database initialization error: {e}')
    # Continue anyway as tables might already exist
"

# Run database migrations if needed
echo "Running database migrations..."
python3 -c "
import os
import sqlite3
from pathlib import Path

# Ensure database directory exists
db_path = Path('./youtube_analytics.db')
db_path.parent.mkdir(parents=True, exist_ok=True)

# Create basic tables if they don't exist
try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check if tables exist, create if not
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utm_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            destination_url TEXT NOT NULL,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            utm_term TEXT,
            utm_content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            click_count INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utm_clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            utm_link_id INTEGER,
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            referrer TEXT,
            FOREIGN KEY (utm_link_id) REFERENCES utm_links (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print('Database migration completed successfully')
except Exception as e:
    print(f'Database migration error: {e}')
"

# Start the FastAPI application
echo "Starting FastAPI server..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
