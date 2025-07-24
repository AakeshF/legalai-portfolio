#!/usr/bin/env python3
"""
Migration script to add AI backend configuration to organizations table
"""
import sqlite3
import sys
from datetime import datetime

def migrate_database():
    """Add AI backend columns to organizations table"""
    
    try:
        # Connect to database
        conn = sqlite3.connect('legal_ai.db')
        cursor = conn.cursor()
        
        print("🔄 Starting migration: Adding AI backend configuration...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(organizations)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add ai_backend column if not exists
        if 'ai_backend' not in columns:
            cursor.execute("""
                ALTER TABLE organizations 
                ADD COLUMN ai_backend VARCHAR DEFAULT 'cloud'
            """)
            print("✅ Added ai_backend column")
        else:
            print("ℹ️  ai_backend column already exists")
        
        # Add local_llm_endpoint column if not exists
        if 'local_llm_endpoint' not in columns:
            cursor.execute("""
                ALTER TABLE organizations 
                ADD COLUMN local_llm_endpoint VARCHAR
            """)
            print("✅ Added local_llm_endpoint column")
        else:
            print("ℹ️  local_llm_endpoint column already exists")
        
        # Add local_llm_model column if not exists
        if 'local_llm_model' not in columns:
            cursor.execute("""
                ALTER TABLE organizations 
                ADD COLUMN local_llm_model VARCHAR
            """)
            print("✅ Added local_llm_model column")
        else:
            print("ℹ️  local_llm_model column already exists")
        
        # Add ai_fallback_enabled column if not exists
        if 'ai_fallback_enabled' not in columns:
            cursor.execute("""
                ALTER TABLE organizations 
                ADD COLUMN ai_fallback_enabled BOOLEAN DEFAULT 1
            """)
            print("✅ Added ai_fallback_enabled column")
        else:
            print("ℹ️  ai_fallback_enabled column already exists")
        
        # Commit changes
        conn.commit()
        
        # Verify migration
        cursor.execute("PRAGMA table_info(organizations)")
        columns = [col[1] for col in cursor.fetchall()]
        
        required_columns = ['ai_backend', 'local_llm_endpoint', 'local_llm_model', 'ai_fallback_enabled']
        missing = [col for col in required_columns if col not in columns]
        
        if missing:
            print(f"❌ Migration incomplete. Missing columns: {missing}")
            return False
        
        print("\n✅ Migration completed successfully!")
        
        # Show current organizations with their AI settings
        cursor.execute("""
            SELECT id, name, ai_backend, local_llm_endpoint, local_llm_model, ai_fallback_enabled
            FROM organizations
        """)
        
        orgs = cursor.fetchall()
        if orgs:
            print("\n📊 Current organizations and AI settings:")
            print("-" * 80)
            for org in orgs:
                print(f"Org: {org[1]}")
                print(f"  Backend: {org[2]}")
                print(f"  Local Endpoint: {org[3] or 'Not configured'}")
                print(f"  Local Model: {org[4] or 'Not configured'}")
                print(f"  Fallback Enabled: {'Yes' if org[5] else 'No'}")
                print("-" * 80)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)