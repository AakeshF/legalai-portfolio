#!/usr/bin/env python3
"""
Initialize database with all required tables
"""
from sqlalchemy import create_engine
from database import Base, engine
import sys

# Import ALL models to register them with Base
from models import Organization, User, Document, ChatSession, ChatMessage
from audit_logger import AuditLog
from session_manager import SecureSession, SessionActivity
from two_factor_auth import TwoFactorAuth
from security_monitor import SecurityIncidentDB


def init_database():
    """Initialize all database tables"""
    try:
        print("🚀 Initializing database with all tables...")

        # Create all tables
        Base.metadata.create_all(bind=engine)

        print("✅ Database initialized successfully!")

        # List all created tables
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"\n📊 Created {len(tables)} tables:")
        for table in sorted(tables):
            print(f"   - {table}")

        return True

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
