"""
Add pretty_slug column to utm_links table for user-friendly redirect URLs.
"""
import sqlite3
import os
from urllib.parse import urlparse
import re

def generate_pretty_slug(destination_url, video_id):
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
            
        # Add video ID suffix to ensure uniqueness
        video_suffix = video_id[:8] if len(video_id) > 8 else video_id
        slug = f"{slug}-{video_suffix}"
        
        # Ensure slug is not too long
        if len(slug) > 80:
            slug = slug[:80]
            
        return slug.lower()
    except Exception:
        # Fallback to simple slug
        return f"link-{video_id}"

def run_migration():
    """Add pretty_slug column and populate it for existing records."""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'youtube_analytics.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add the pretty_slug column (without UNIQUE constraint initially)
        print("Adding pretty_slug column to utm_links table...")
        cursor.execute("""
            ALTER TABLE utm_links
            ADD COLUMN pretty_slug VARCHAR(100)
        """)
        
        # Get existing UTM links
        cursor.execute("""
            SELECT id, destination_url, video_id 
            FROM utm_links 
            WHERE pretty_slug IS NULL
        """)
        
        existing_links = cursor.fetchall()
        print(f"Found {len(existing_links)} existing UTM links to update...")
        
        # Generate pretty slugs for existing links
        for link_id, destination_url, video_id in existing_links:
            pretty_slug = generate_pretty_slug(destination_url, video_id)
            
            # Ensure uniqueness
            counter = 1
            original_slug = pretty_slug
            while True:
                cursor.execute("SELECT id FROM utm_links WHERE pretty_slug = ?", (pretty_slug,))
                if cursor.fetchone() is None:
                    break
                counter += 1
                pretty_slug = f"{original_slug}-{counter}"
            
            # Update the record
            cursor.execute("""
                UPDATE utm_links 
                SET pretty_slug = ? 
                WHERE id = ?
            """, (pretty_slug, link_id))
            
            print(f"  Updated link {link_id}: {pretty_slug}")
        
        conn.commit()
        print("Migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
