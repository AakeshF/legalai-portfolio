#!/usr/bin/env python3
"""
Migration script to add client communication tracking tables
"""

import sys
import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from database import engine, Base
from models import ClientCommunication, CommunicationFollowUp, CommunicationTemplate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_communication_tables():
    """Add communication tracking tables if they don't exist"""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        tables_to_create = []
        
        # Check which tables need to be created
        if 'client_communications' not in existing_tables:
            tables_to_create.append('client_communications')
        if 'communication_follow_ups' not in existing_tables:
            tables_to_create.append('communication_follow_ups')
        if 'communication_templates' not in existing_tables:
            tables_to_create.append('communication_templates')
            
        if not tables_to_create:
            logger.info("All communication tables already exist")
            return True
            
        logger.info(f"Creating tables: {', '.join(tables_to_create)}")
        
        # Create only the missing tables
        Base.metadata.create_all(bind=engine, tables=[
            table for table in Base.metadata.sorted_tables 
            if table.name in tables_to_create
        ])
        
        logger.info("Communication tables created successfully")
        
        # Verify creation
        inspector = inspect(engine)
        new_tables = inspector.get_table_names()
        
        for table in tables_to_create:
            if table in new_tables:
                logger.info(f"✓ Table '{table}' created successfully")
            else:
                logger.error(f"✗ Failed to create table '{table}'")
                return False
                
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database error during migration: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during migration: {str(e)}")
        return False

def verify_migration():
    """Verify the migration was successful"""
    try:
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Test querying each table
        tables = [
            (ClientCommunication, "client_communications"),
            (CommunicationFollowUp, "communication_follow_ups"),
            (CommunicationTemplate, "communication_templates")
        ]
        
        for model, table_name in tables:
            count = session.query(model).count()
            logger.info(f"Table '{table_name}' is accessible (rows: {count})")
            
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"Error verifying migration: {str(e)}")
        return False

def main():
    """Run the migration"""
    logger.info("Starting client communication tables migration...")
    
    # Create tables
    if not add_communication_tables():
        logger.error("Failed to create tables")
        sys.exit(1)
        
    # Verify
    if not verify_migration():
        logger.error("Failed to verify migration")
        sys.exit(1)
        
    logger.info("\nMigration completed successfully!")
    logger.info("\nNew features available:")
    logger.info("- Comprehensive client communication tracking")
    logger.info("- Attorney-client privilege protection")
    logger.info("- Automated privilege log generation")
    logger.info("- Smart follow-up system with escalation")
    logger.info("- Integration with email, phone, SMS, and calendar systems")
    logger.info("- Communication templates for consistent messaging")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)