#!/usr/bin/env python3
"""
Migration script for enhanced discount system
Run this from jupiter_backend directory: python migrate_discount_system.py
"""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

async def migrate_discount_system():
    """Migrate the database for enhanced discount system"""
    
    # Load environment variables
    load_dotenv()
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return
    
    # Create async engine
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    try:
        async with async_session() as session:
            print("🚀 Starting discount system migration...")
            
            # Step 1: Add new columns to discount_rules table
            print("📝 Adding new columns to discount_rules table...")
            
            new_columns = [
                "ADD COLUMN IF NOT EXISTS description TEXT",
                "ADD COLUMN IF NOT EXISTS discount_type VARCHAR DEFAULT 'percentage'",
                "ADD COLUMN IF NOT EXISTS valid_from TIMESTAMP DEFAULT NOW()",
                "ADD COLUMN IF NOT EXISTS valid_until TIMESTAMP",
                "ADD COLUMN IF NOT EXISTS validity_days INTEGER",
                "ADD COLUMN IF NOT EXISTS auto_apply BOOLEAN DEFAULT FALSE",
                "ADD COLUMN IF NOT EXISTS max_uses_per_user INTEGER",
                "ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",
                "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()"
            ]
            
            for column in new_columns:
                try:
                    await session.execute(text(f"ALTER TABLE discount_rules {column}"))
                    print(f"✅ Added: {column}")
                except Exception as e:
                    print(f"⚠️ Column might exist: {column}")
            
            # Step 2: Create user_discount_enrollments table
            print("📝 Creating user_discount_enrollments table...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS user_discount_enrollments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    discount_rule_id INTEGER NOT NULL REFERENCES discount_rules(id) ON DELETE CASCADE,
                    enrolled_at TIMESTAMP DEFAULT NOW(),
                    valid_until TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    UNIQUE(user_id, discount_rule_id)
                );
            """))
            print("✅ Created user_discount_enrollments table")
            
            # Step 3: Create user_notifications table
            print("📝 Creating user_notifications table...")
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS user_notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR NOT NULL,
                    message TEXT NOT NULL,
                    notification_type VARCHAR DEFAULT 'discount',
                    discount_rule_id INTEGER REFERENCES discount_rules(id) ON DELETE CASCADE,
                    extra_data TEXT,
                    is_read BOOLEAN DEFAULT FALSE,
                    is_popup_shown BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    read_at TIMESTAMP
                );
            """))
            print("✅ Created user_notifications table")
            
            # Step 4: Create indexes for performance
            print("📝 Creating indexes...")
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_user_discount_enrollments_user_id ON user_discount_enrollments(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_discount_enrollments_active ON user_discount_enrollments(user_id, is_active)",
                "CREATE INDEX IF NOT EXISTS idx_user_notifications_user_id ON user_notifications(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_user_notifications_unread ON user_notifications(user_id, is_read)",
                "CREATE INDEX IF NOT EXISTS idx_discount_rules_model_active ON discount_rules(model_id, is_active)"
            ]
            
            for index in indexes:
                try:
                    await session.execute(text(index))
                    print(f"✅ Created index")
                except Exception as e:
                    print(f"⚠️ Index might exist")
            
            await session.commit()
            print("🎉 Migration completed successfully!")
            
            # Step 5: Show current table structure
            print("\n📊 Updated table structures:")
            
            # Show discount_rules columns
            result = await session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'discount_rules' 
                ORDER BY ordinal_position;
            """))
            print("\ndiscount_rules table columns:")
            for row in result:
                print(f"  - {row.column_name}: {row.data_type}")
            
            # Show new tables
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name IN ('user_discount_enrollments', 'user_notifications')
                AND table_schema = 'public';
            """))
            print(f"\nNew tables created:")
            for row in result:
                print(f"  ✅ {row.table_name}")
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_discount_system())
