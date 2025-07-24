# migrations/add_ai_management_tables.py - Migration for AI management tables
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import engine
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Add AI management, consent, and audit trail tables"""
    
    with engine.connect() as conn:
        # Create API Key Store table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_key_store (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id TEXT NOT NULL REFERENCES organizations(id),
                provider VARCHAR(50) NOT NULL,
                encrypted_key TEXT NOT NULL,
                key_hint VARCHAR(20),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT REFERENCES users(id),
                last_validated TIMESTAMP,
                validation_status VARCHAR(20),
                last_used TIMESTAMP,
                usage_count INTEGER DEFAULT 0
            )
        """))
        
        # Create indexes for api_key_store
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_api_key_org_provider ON api_key_store(organization_id, provider)"))
        
        # Create Consent Records table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS consent_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id TEXT NOT NULL REFERENCES organizations(id),
                user_id TEXT REFERENCES users(id),
                document_id TEXT REFERENCES documents(id),
                consent_type VARCHAR(50) NOT NULL,
                consent_scope VARCHAR(50) NOT NULL,
                granted BOOLEAN NOT NULL,
                purpose TEXT,
                data_categories TEXT,
                providers_allowed TEXT,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                revoked_at TIMESTAMP,
                granted_by TEXT REFERENCES users(id),
                ip_address VARCHAR(45),
                user_agent VARCHAR(255),
                legal_basis VARCHAR(50),
                version VARCHAR(20)
            )
        """))
        
        # Create indexes for consent_records
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_consent_org_type ON consent_records(organization_id, consent_type)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_consent_user ON consent_records(user_id)"))
        
        # Create Consent Preferences table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS consent_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id TEXT UNIQUE NOT NULL REFERENCES organizations(id),
                require_explicit_consent BOOLEAN DEFAULT 1,
                default_ai_provider VARCHAR(50),
                allowed_providers TEXT,
                allow_cloud_processing BOOLEAN DEFAULT 1,
                require_local_only BOOLEAN DEFAULT 0,
                data_retention_days INTEGER DEFAULT 90,
                notify_on_processing BOOLEAN DEFAULT 0,
                consent_renewal_days INTEGER DEFAULT 365,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create AI Audit Logs table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id TEXT NOT NULL REFERENCES organizations(id),
                user_id TEXT NOT NULL REFERENCES users(id),
                request_id VARCHAR(36) UNIQUE NOT NULL,
                request_type VARCHAR(50),
                request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                provider_used VARCHAR(50) NOT NULL,
                model_used VARCHAR(100),
                provider_fallback VARCHAR(200),
                input_hash VARCHAR(64),
                input_size INTEGER,
                document_ids TEXT,
                output_hash VARCHAR(64),
                output_size INTEGER,
                response_time_ms INTEGER,
                consent_id INTEGER REFERENCES consent_records(id),
                consent_verified VARCHAR(20),
                tokens_used INTEGER,
                estimated_cost REAL,
                decision_type VARCHAR(100),
                decision_summary TEXT,
                confidence_score REAL,
                processing_location VARCHAR(50),
                data_residency VARCHAR(50),
                retention_expires TIMESTAMP,
                anonymized TIMESTAMP,
                deleted TIMESTAMP
            )
        """))
        
        # Create indexes for ai_audit_logs
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_request_id ON ai_audit_logs(request_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_org_timestamp ON ai_audit_logs(organization_id, request_timestamp)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp ON ai_audit_logs(user_id, request_timestamp)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_audit_provider_timestamp ON ai_audit_logs(provider_used, request_timestamp)"))
        
        # Create AI Decision Details table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_decision_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_log_id INTEGER NOT NULL REFERENCES ai_audit_logs(id),
                decision_category VARCHAR(50),
                decision_item VARCHAR(200),
                decision_value TEXT,
                confidence REAL,
                evidence_type VARCHAR(50),
                evidence_reference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create index for ai_decision_details
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_decision_audit_log ON ai_decision_details(audit_log_id)"))
        
        conn.commit()
        
    logger.info("Successfully created AI management tables")

def downgrade():
    """Remove AI management tables"""
    
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS ai_decision_details"))
        conn.execute(text("DROP TABLE IF EXISTS ai_audit_logs"))
        conn.execute(text("DROP TABLE IF EXISTS consent_preferences"))
        conn.execute(text("DROP TABLE IF EXISTS consent_records"))
        conn.execute(text("DROP TABLE IF EXISTS api_key_store"))
        conn.commit()
        
    logger.info("Successfully removed AI management tables")

if __name__ == "__main__":
    upgrade()
    print("✅ AI management tables created successfully")