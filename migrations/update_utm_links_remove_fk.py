#!/usr/bin/env python3
"""
Database migration to remove foreign key constraint from utm_links table
to allow tracking new videos that haven't been uploaded yet.
"""
import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings


def update_utm_links_table():
    """Remove foreign key constraint from utm_links table."""
    
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            print("🔧 Updating utm_links table to remove foreign key constraint...")
            
            # For SQLite, we need to recreate the table without the foreign key
            # First, create a backup of existing data
            print("📊 Backing up existing UTM links data...")
            backup_result = connection.execute(text("SELECT * FROM utm_links"))
            existing_data = backup_result.fetchall()
            print(f"   Found {len(existing_data)} existing UTM links")
            
            # Drop the existing table
            print("🗑️  Dropping existing utm_links table...")
            connection.execute(text("DROP TABLE IF EXISTS utm_links"))
            
            # Recreate the table without foreign key constraint
            print("🏗️  Creating new utm_links table without foreign key...")
            utm_links_table = """
            CREATE TABLE utm_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id VARCHAR(255) NOT NULL,
                destination_url TEXT NOT NULL,
                utm_source VARCHAR(100) NOT NULL DEFAULT 'youtube',
                utm_medium VARCHAR(100) NOT NULL DEFAULT 'video',
                utm_campaign VARCHAR(255) NOT NULL,
                utm_content VARCHAR(255),
                utm_term VARCHAR(255),
                tracking_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            );
            """
            connection.execute(text(utm_links_table))
            
            # Recreate indexes
            print("🔍 Creating indexes...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_utm_video_active ON utm_links (video_id, is_active);",
                "CREATE INDEX IF NOT EXISTS idx_utm_created ON utm_links (created_at);",
                "CREATE INDEX IF NOT EXISTS idx_utm_video_id ON utm_links (video_id);"
            ]
            
            for index_sql in indexes:
                connection.execute(text(index_sql))
            
            # Restore existing data if any
            if existing_data:
                print(f"📥 Restoring {len(existing_data)} existing UTM links...")
                
                # Get column names from the backup
                columns = [
                    'video_id', 'destination_url', 'utm_source', 'utm_medium', 
                    'utm_campaign', 'utm_content', 'utm_term', 'tracking_url',
                    'created_at', 'updated_at', 'is_active'
                ]
                
                # Insert each row back
                for row in existing_data:
                    # Skip the id column (index 0) as it's auto-increment
                    values = [f"'{str(val)}'" if val is not None else 'NULL' for val in row[1:]]
                    insert_sql = f"""
                    INSERT INTO utm_links ({', '.join(columns)}) 
                    VALUES ({', '.join(values)})
                    """
                    connection.execute(text(insert_sql))
            
            # Commit the transaction
            connection.commit()
            
            print("✅ UTM links table updated successfully!")
            print("🎯 Benefits:")
            print("   - Can now create UTM links for new videos before they're uploaded")
            print("   - No foreign key constraint blocking new video IDs")
            print("   - Existing UTM links preserved")
            
    except Exception as e:
        print(f"❌ Error updating utm_links table: {str(e)}")
        return False
    
    return True


def verify_update():
    """Verify that the utm_links table was updated successfully."""
    engine = create_engine(settings.DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            print("\n🔍 Verifying table update...")
            
            # Check table structure
            result = connection.execute(text("PRAGMA table_info(utm_links);"))
            columns = result.fetchall()
            print(f"✅ utm_links table has {len(columns)} columns")
            
            # Check for foreign key constraints
            result = connection.execute(text("PRAGMA foreign_key_list(utm_links);"))
            foreign_keys = result.fetchall()
            
            if len(foreign_keys) == 0:
                print("✅ No foreign key constraints found (as expected)")
            else:
                print(f"⚠️  Found {len(foreign_keys)} foreign key constraints")
                for fk in foreign_keys:
                    print(f"     - {fk}")
            
            # Check existing data
            result = connection.execute(text("SELECT COUNT(*) FROM utm_links;"))
            count = result.scalar()
            print(f"📊 UTM links table contains {count} records")
            
            print("\n✅ Table update verification completed!")
            
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False
    
    return True


def main():
    """Main migration function."""
    print("🔄 UTM Links Table Update Migration")
    print("=" * 50)
    print(f"📅 Migration started at: {datetime.now()}")
    print(f"🗄️  Database: {settings.DATABASE_URL}")
    print()
    print("🎯 Purpose: Remove foreign key constraint to allow tracking new videos")
    print()
    
    # Update table
    if not update_utm_links_table():
        print("\n❌ Migration failed!")
        sys.exit(1)
    
    # Verify update
    if not verify_update():
        print("\n❌ Verification failed!")
        sys.exit(1)
    
    print(f"\n🎉 Migration completed successfully at: {datetime.now()}")
    print("\n🚀 UTM Link Generator Enhanced!")
    print("✨ You can now:")
    print("   1. Create UTM links for new videos before uploading")
    print("   2. Track clicks for videos not yet in your database")
    print("   3. Generate tracking links for any YouTube video ID")
    print("   4. Monitor performance as soon as videos go live")


if __name__ == "__main__":
    main()
