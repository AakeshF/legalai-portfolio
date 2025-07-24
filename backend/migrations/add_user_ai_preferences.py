# migrations/add_user_ai_preferences.py - Add AI preferences and budget fields
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from database import engine
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Add AI preferences to users and budget fields to organizations"""
    
    with engine.connect() as conn:
        # Add columns to users table
        try:
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN ai_provider_preference VARCHAR(50)
            """))
        except Exception as e:
            logger.info(f"Column ai_provider_preference may already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN ai_model_preferences TEXT
            """))
        except Exception as e:
            logger.info(f"Column ai_model_preferences may already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN ai_consent_given BOOLEAN DEFAULT 0
            """))
        except Exception as e:
            logger.info(f"Column ai_consent_given may already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE users ADD COLUMN ai_consent_date TIMESTAMP
            """))
        except Exception as e:
            logger.info(f"Column ai_consent_date may already exist: {e}")
        
        # Add columns to organizations table
        try:
            conn.execute(text("""
                ALTER TABLE organizations ADD COLUMN ai_monthly_budget REAL
            """))
        except Exception as e:
            logger.info(f"Column ai_monthly_budget may already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE organizations ADD COLUMN ai_budget_alert_threshold REAL DEFAULT 0.8
            """))
        except Exception as e:
            logger.info(f"Column ai_budget_alert_threshold may already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE organizations ADD COLUMN ai_budget_period_start TIMESTAMP
            """))
        except Exception as e:
            logger.info(f"Column ai_budget_period_start may already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE organizations ADD COLUMN ai_current_month_cost REAL DEFAULT 0.0
            """))
        except Exception as e:
            logger.info(f"Column ai_current_month_cost may already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE organizations ADD COLUMN ai_cost_alerts_enabled BOOLEAN DEFAULT 1
            """))
        except Exception as e:
            logger.info(f"Column ai_cost_alerts_enabled may already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE organizations ADD COLUMN ai_max_tokens_per_request INTEGER DEFAULT 4000
            """))
        except Exception as e:
            logger.info(f"Column ai_max_tokens_per_request may already exist: {e}")
        
        try:
            conn.execute(text("""
                ALTER TABLE organizations ADD COLUMN ai_rate_limit_per_minute INTEGER DEFAULT 10
            """))
        except Exception as e:
            logger.info(f"Column ai_rate_limit_per_minute may already exist: {e}")
        
        conn.commit()
        
    logger.info("Successfully added AI preference and budget columns")

def downgrade():
    """Remove AI preference and budget columns"""
    
    with engine.connect() as conn:
        # Remove user columns
        conn.execute(text("ALTER TABLE users DROP COLUMN ai_provider_preference"))
        conn.execute(text("ALTER TABLE users DROP COLUMN ai_model_preferences"))
        conn.execute(text("ALTER TABLE users DROP COLUMN ai_consent_given"))
        conn.execute(text("ALTER TABLE users DROP COLUMN ai_consent_date"))
        
        # Remove organization columns
        conn.execute(text("ALTER TABLE organizations DROP COLUMN ai_monthly_budget"))
        conn.execute(text("ALTER TABLE organizations DROP COLUMN ai_budget_alert_threshold"))
        conn.execute(text("ALTER TABLE organizations DROP COLUMN ai_budget_period_start"))
        conn.execute(text("ALTER TABLE organizations DROP COLUMN ai_current_month_cost"))
        conn.execute(text("ALTER TABLE organizations DROP COLUMN ai_cost_alerts_enabled"))
        conn.execute(text("ALTER TABLE organizations DROP COLUMN ai_max_tokens_per_request"))
        conn.execute(text("ALTER TABLE organizations DROP COLUMN ai_rate_limit_per_minute"))
        
        conn.commit()
        
    logger.info("Successfully removed AI preference and budget columns")

if __name__ == "__main__":
    upgrade()
    print("✅ AI preference and budget columns added successfully")