#!/usr/bin/env python3
# migrate_add_multitenancy.py - Database migration script to add multi-tenancy support

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError
from datetime import datetime
import uuid

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from models import Base, Organization, User, Document, ChatSession
from config import settings
from auth_utils import hash_password

def create_tables():
    """Create new tables for organizations and users"""
    print("Creating new tables...")
    
    # Create all tables (this will only create new ones)
    Base.metadata.create_all(bind=engine)
    
    print("✅ Tables created successfully")

def add_missing_columns():
    """Add organization_id columns to existing tables"""
    print("\nAdding organization_id columns to existing tables...")
    
    with engine.connect() as conn:
        inspector = inspect(engine)
        
        # Check if columns already exist
        document_columns = [col['name'] for col in inspector.get_columns('documents')]
        session_columns = [col['name'] for col in inspector.get_columns('chat_sessions')]
        
        try:
            # Add organization_id to documents table if missing
            if 'organization_id' not in document_columns:
                print("Adding organization_id to documents table...")
                conn.execute(text("""
                    ALTER TABLE documents 
                    ADD COLUMN organization_id VARCHAR
                """))
                conn.commit()
            
            # Add uploaded_by_id to documents table if missing
            if 'uploaded_by_id' not in document_columns:
                print("Adding uploaded_by_id to documents table...")
                conn.execute(text("""
                    ALTER TABLE documents 
                    ADD COLUMN uploaded_by_id VARCHAR
                """))
                conn.commit()
            
            # Add organization_id to chat_sessions table if missing
            if 'organization_id' not in session_columns:
                print("Adding organization_id to chat_sessions table...")
                conn.execute(text("""
                    ALTER TABLE chat_sessions 
                    ADD COLUMN organization_id VARCHAR
                """))
                conn.commit()
            
            # Add user_id to chat_sessions table if missing
            if 'user_id' not in session_columns:
                print("Adding user_id to chat_sessions table...")
                conn.execute(text("""
                    ALTER TABLE chat_sessions 
                    ADD COLUMN user_id VARCHAR
                """))
                conn.commit()
            
            print("✅ Columns added successfully")
            
        except Exception as e:
            print(f"Note: Some columns may already exist - {str(e)}")

def create_default_organization():
    """Create a default organization for existing data"""
    print("\nCreating default organization...")
    
    db = SessionLocal()
    try:
        # Check if default org exists
        default_org = db.query(Organization).filter(
            Organization.name == "Default Organization"
        ).first()
        
        if not default_org:
            # Create default organization
            default_org = Organization(
                id=str(uuid.uuid4()),
                name="Default Organization",
                subscription_tier="basic",
                billing_email="[ADMIN-EMAIL]",
                created_at=datetime.utcnow(),
                is_active=True
            )
            db.add(default_org)
            db.commit()
            print(f"✅ Created default organization with ID: {default_org.id}")
        else:
            print(f"✅ Default organization already exists with ID: {default_org.id}")
        
        return default_org.id
        
    finally:
        db.close()

def create_default_admin(org_id: str):
    """Create a default admin user"""
    print("\nCreating default admin user...")
    
    db = SessionLocal()
    try:
        # Check if admin exists
        admin = db.query(User).filter(User.email == "[ADMIN-EMAIL]").first()
        
        if not admin:
            # Create admin user
            admin = User(
                id=str(uuid.uuid4()),
                email="[ADMIN-EMAIL]",
                password_hash=hash_password("Admin123!"),  # Default password
                first_name="System",
                last_name="Administrator",
                role="admin",
                organization_id=org_id,
                created_at=datetime.utcnow(),
                is_active=True
            )
            db.add(admin)
            db.commit()
            print(f"✅ Created admin user with email: [ADMIN-EMAIL]")
            print("⚠️  Default password is: Admin123! (Please change immediately)")
        else:
            print(f"✅ Admin user already exists")
        
        return admin.id
        
    finally:
        db.close()

def migrate_existing_data(org_id: str):
    """Migrate existing documents and chat sessions to default organization"""
    print("\nMigrating existing data to default organization...")
    
    with engine.connect() as conn:
        # Update documents
        result = conn.execute(text("""
            UPDATE documents 
            SET organization_id = :org_id 
            WHERE organization_id IS NULL
        """), {"org_id": org_id})
        conn.commit()
        print(f"✅ Migrated {result.rowcount} documents")
        
        # Update chat sessions
        result = conn.execute(text("""
            UPDATE chat_sessions 
            SET organization_id = :org_id 
            WHERE organization_id IS NULL
        """), {"org_id": org_id})
        conn.commit()
        print(f"✅ Migrated {result.rowcount} chat sessions")

def add_indexes():
    """Add indexes for better performance"""
    print("\nAdding indexes...")
    
    with engine.connect() as conn:
        try:
            # Organization indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id)"))
            
            # Document indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_organization ON documents(organization_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by_id)"))
            
            # Chat session indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_sessions_organization ON chat_sessions(organization_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)"))
            
            conn.commit()
            print("✅ Indexes created successfully")
            
        except Exception as e:
            print(f"Note: Some indexes may already exist - {str(e)}")

def main():
    """Run the migration"""
    print("🚀 Starting multi-tenancy migration...")
    print(f"Database: {settings.database_url}")
    
    try:
        # Step 1: Create new tables
        create_tables()
        
        # Step 2: Add missing columns
        add_missing_columns()
        
        # Step 3: Create default organization
        default_org_id = create_default_organization()
        
        # Step 4: Create default admin user
        create_default_admin(default_org_id)
        
        # Step 5: Migrate existing data
        migrate_existing_data(default_org_id)
        
        # Step 6: Add indexes
        add_indexes()
        
        print("\n✅ Migration completed successfully!")
        print("\n📝 Next steps:")
        print("1. Update your .env file with JWT_SECRET_KEY")
        print("2. Login with [ADMIN-EMAIL] / Admin123!")
        print("3. Create your organization and users")
        print("4. Update API endpoints to require authentication")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()