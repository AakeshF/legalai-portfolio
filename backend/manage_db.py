#!/usr/bin/env python
# manage_db.py - Database management script for production
import os
import sys
import argparse
import logging
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError

from database import Base, engine
from models import Document, ChatSession, ChatMessage
from config import settings
from logger import setup_logging, get_logger

# Setup logging
setup_logging(log_format="simple")
logger = get_logger(__name__)

class DatabaseManager:
    """Manage database operations for production deployment"""
    
    def __init__(self):
        self.engine = engine
        self.alembic_cfg = Config("alembic.ini")
        
    def check_connection(self):
        """Check if database is accessible"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
        except OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def create_database(self):
        """Create database if it doesn't exist (PostgreSQL only)"""
        if "postgresql" not in settings.database_url:
            logger.info("Skipping database creation for SQLite")
            return
        
        # Parse database URL
        db_url_parts = settings.database_url.split("/")
        db_name = db_url_parts[-1].split("?")[0]
        server_url = "/".join(db_url_parts[:-1]) + "/postgres"
        
        try:
            # Connect to postgres database
            temp_engine = create_engine(server_url)
            with temp_engine.connect() as conn:
                # Check if database exists
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": db_name}
                )
                if not result.fetchone():
                    # Create database
                    conn.execute(text(f"CREATE DATABASE {db_name}"))
                    logger.info(f"Created database: {db_name}")
                else:
                    logger.info(f"Database already exists: {db_name}")
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            raise
    
    def init_alembic(self):
        """Initialize Alembic if not already initialized"""
        try:
            # Check if alembic version table exists
            inspector = inspect(self.engine)
            if "alembic_version" not in inspector.get_table_names():
                logger.info("Initializing Alembic...")
                command.stamp(self.alembic_cfg, "head")
                logger.info("Alembic initialized")
            else:
                logger.info("Alembic already initialized")
        except Exception as e:
            logger.error(f"Error initializing Alembic: {e}")
            raise
    
    def create_tables(self):
        """Create all tables using SQLAlchemy"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    def generate_migration(self, message):
        """Generate a new migration"""
        try:
            command.revision(self.alembic_cfg, autogenerate=True, message=message)
            logger.info(f"Generated migration: {message}")
        except Exception as e:
            logger.error(f"Error generating migration: {e}")
            raise
    
    def run_migrations(self):
        """Run all pending migrations"""
        try:
            command.upgrade(self.alembic_cfg, "head")
            logger.info("Migrations completed successfully")
        except Exception as e:
            logger.error(f"Error running migrations: {e}")
            raise
    
    def rollback_migration(self, revision="-1"):
        """Rollback to a specific revision"""
        try:
            command.downgrade(self.alembic_cfg, revision)
            logger.info(f"Rolled back to revision: {revision}")
        except Exception as e:
            logger.error(f"Error rolling back migration: {e}")
            raise
    
    def show_current_revision(self):
        """Show current database revision"""
        try:
            command.current(self.alembic_cfg)
        except Exception as e:
            logger.error(f"Error showing current revision: {e}")
            raise
    
    def show_migration_history(self):
        """Show migration history"""
        try:
            command.history(self.alembic_cfg)
        except Exception as e:
            logger.error(f"Error showing migration history: {e}")
            raise
    
    def create_indexes(self):
        """Create database indexes for better performance"""
        indexes = [
            # Document indexes
            "CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename)",
            "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(processing_status)",
            "CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_documents_file_size ON documents(file_size)",
            
            # Full-text search indexes (PostgreSQL)
            "CREATE INDEX IF NOT EXISTS idx_documents_content_search ON documents USING gin(to_tsvector('english', extracted_content))",
            "CREATE INDEX IF NOT EXISTS idx_documents_summary_search ON documents USING gin(to_tsvector('english', summary))",
            
            # Chat indexes
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at DESC)",
        ]
        
        with self.engine.connect() as conn:
            for index_sql in indexes:
                try:
                    # Skip PostgreSQL-specific indexes for SQLite
                    if "gin" in index_sql and "sqlite" in settings.database_url:
                        continue
                    
                    conn.execute(text(index_sql))
                    conn.commit()
                    logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    logger.warning(f"Could not create index: {e}")
    
    def vacuum_database(self):
        """Vacuum database to reclaim space and update statistics"""
        try:
            with self.engine.connect() as conn:
                if "postgresql" in settings.database_url:
                    conn.execute(text("VACUUM ANALYZE"))
                elif "sqlite" in settings.database_url:
                    conn.execute(text("VACUUM"))
            logger.info("Database vacuum completed")
        except Exception as e:
            logger.error(f"Error vacuuming database: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(description="Legal AI Database Management")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Commands
    subparsers.add_parser("check", help="Check database connection")
    subparsers.add_parser("create", help="Create database (PostgreSQL only)")
    subparsers.add_parser("init", help="Initialize database with tables")
    subparsers.add_parser("migrate", help="Run database migrations")
    
    migration_parser = subparsers.add_parser("generate", help="Generate new migration")
    migration_parser.add_argument("message", help="Migration message")
    
    rollback_parser = subparsers.add_parser("rollback", help="Rollback migration")
    rollback_parser.add_argument("--revision", default="-1", help="Target revision")
    
    subparsers.add_parser("current", help="Show current revision")
    subparsers.add_parser("history", help="Show migration history")
    subparsers.add_parser("indexes", help="Create database indexes")
    subparsers.add_parser("vacuum", help="Vacuum database")
    subparsers.add_parser("setup", help="Full database setup (create, init, migrate, indexes)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    db_manager = DatabaseManager()
    
    try:
        if args.command == "check":
            if db_manager.check_connection():
                print("✅ Database connection successful")
            else:
                print("❌ Database connection failed")
                sys.exit(1)
        
        elif args.command == "create":
            db_manager.create_database()
            print("✅ Database created")
        
        elif args.command == "init":
            db_manager.create_tables()
            db_manager.init_alembic()
            print("✅ Database initialized")
        
        elif args.command == "migrate":
            db_manager.run_migrations()
            print("✅ Migrations completed")
        
        elif args.command == "generate":
            db_manager.generate_migration(args.message)
            print(f"✅ Migration generated: {args.message}")
        
        elif args.command == "rollback":
            db_manager.rollback_migration(args.revision)
            print(f"✅ Rolled back to revision: {args.revision}")
        
        elif args.command == "current":
            db_manager.show_current_revision()
        
        elif args.command == "history":
            db_manager.show_migration_history()
        
        elif args.command == "indexes":
            db_manager.create_indexes()
            print("✅ Indexes created")
        
        elif args.command == "vacuum":
            db_manager.vacuum_database()
            print("✅ Database vacuum completed")
        
        elif args.command == "setup":
            print("🚀 Running full database setup...")
            db_manager.create_database()
            db_manager.create_tables()
            db_manager.init_alembic()
            db_manager.run_migrations()
            db_manager.create_indexes()
            print("✅ Database setup completed")
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()