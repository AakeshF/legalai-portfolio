-- init.sql - Initial database setup for PostgreSQL
-- This file is used by docker-compose to initialize the database

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For full-text search

-- Create indexes for better performance
-- These will be created after tables are created by Alembic

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Grant permissions to application user
-- Note: Replace 'legalai' with your actual database user
GRANT ALL PRIVILEGES ON SCHEMA public TO legalai;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO legalai;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO legalai;