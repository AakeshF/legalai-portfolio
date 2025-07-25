#!/usr/bin/env python3
"""
Migration script to add matter management tables with MCP integration support
"""

import sys
import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from database import engine, Base
from models import Matter, Deadline, Communication, MCPQueryCache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_matter_management_tables():
    """Add matter management tables if they don't exist"""
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        tables_to_create = []

        # Check which tables need to be created
        if "matters" not in existing_tables:
            tables_to_create.append("matters")
        if "deadlines" not in existing_tables:
            tables_to_create.append("deadlines")
        if "communications" not in existing_tables:
            tables_to_create.append("communications")
        if "mcp_query_cache" not in existing_tables:
            tables_to_create.append("mcp_query_cache")

        if not tables_to_create:
            logger.info("All matter management tables already exist")
            return True

        logger.info(f"Creating tables: {', '.join(tables_to_create)}")

        # Create only the missing tables
        Base.metadata.create_all(
            bind=engine,
            tables=[
                table
                for table in Base.metadata.sorted_tables
                if table.name in tables_to_create
            ],
        )

        logger.info("Matter management tables created successfully")

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


def main():
    """Main migration function"""
    logger.info("Starting matter management migration...")

    try:
        # Add matter management tables
        if not add_matter_management_tables():
            logger.error("Failed to add matter management tables")
            sys.exit(1)

        logger.info("Migration completed successfully!")
        logger.info("\nNew features available:")
        logger.info("- Matter management with conflict checking")
        logger.info("- MCP integration for court data, calendar, and email sync")
        logger.info("- Deadline tracking with MCP synchronization")
        logger.info("- Communication logging with email integration")
        logger.info("- Query caching for improved performance")

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
