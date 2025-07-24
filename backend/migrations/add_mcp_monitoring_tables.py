"""
Add MCP Monitoring Tables Migration

Creates tables for MCP server monitoring, performance metrics,
health status tracking, alerts, and cache analytics.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Column, String, DateTime, Text, Boolean, JSON, Float, Index
from datetime import datetime
import uuid

# Migration details
revision = 'add_mcp_monitoring'
down_revision = 'add_communication_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create MCP monitoring tables"""
    
    # Create MCP metrics table
    op.create_table(
        'mcp_metrics',
        Column('id', String, primary_key=True, default=lambda: str(uuid.uuid4())),
        Column('server_name', String, nullable=False, index=True),
        Column('action', String, nullable=False, index=True),
        Column('duration', Float, nullable=False),
        Column('success', Boolean, nullable=False),
        Column('error', String, nullable=True),
        Column('timestamp', DateTime, nullable=False, index=True),
        Column('metadata', JSON, default=dict)
    )
    
    # Create compound index for performance queries
    op.create_index(
        'idx_mcp_metrics_server_timestamp',
        'mcp_metrics',
        ['server_name', 'timestamp']
    )
    
    op.create_index(
        'idx_mcp_metrics_action_timestamp',
        'mcp_metrics',
        ['action', 'timestamp']
    )
    
    # Create MCP health status table
    op.create_table(
        'mcp_health_status',
        Column('id', String, primary_key=True, default=lambda: str(uuid.uuid4())),
        Column('server_name', String, nullable=False, unique=True, index=True),
        Column('status', String, nullable=False),
        Column('response_time', Float, nullable=True),
        Column('last_check', DateTime, nullable=False),
        Column('error', String, nullable=True),
        Column('metadata', JSON, default=dict)
    )
    
    # Create MCP alerts table
    op.create_table(
        'mcp_alerts',
        Column('id', String, primary_key=True, default=lambda: str(uuid.uuid4())),
        Column('severity', String, nullable=False, index=True),
        Column('type', String, nullable=False),
        Column('server_name', String, nullable=True, index=True),
        Column('message', Text, nullable=False),
        Column('metadata', JSON, default=dict),
        Column('created_at', DateTime, nullable=False, index=True),
        Column('resolved', Boolean, default=False, index=True),
        Column('resolved_at', DateTime, nullable=True)
    )
    
    # Create compound index for active alerts
    op.create_index(
        'idx_mcp_alerts_active',
        'mcp_alerts',
        ['resolved', 'severity', 'created_at']
    )
    
    # Create MCP cache metrics table
    op.create_table(
        'mcp_cache_metrics',
        Column('id', String, primary_key=True, default=lambda: str(uuid.uuid4())),
        Column('cache_name', String, nullable=False, index=True),
        Column('event_type', String, nullable=False, index=True),
        Column('key', String, nullable=False),
        Column('timestamp', DateTime, nullable=False, index=True),
        Column('metadata', JSON, default=dict)
    )
    
    # Create compound index for cache analysis
    op.create_index(
        'idx_mcp_cache_metrics_cache_event',
        'mcp_cache_metrics',
        ['cache_name', 'event_type', 'timestamp']
    )
    
    print("✅ Created MCP monitoring tables:")
    print("  - mcp_metrics")
    print("  - mcp_health_status")
    print("  - mcp_alerts")
    print("  - mcp_cache_metrics")


def downgrade():
    """Drop MCP monitoring tables"""
    
    # Drop indexes first
    op.drop_index('idx_mcp_cache_metrics_cache_event', 'mcp_cache_metrics')
    op.drop_index('idx_mcp_alerts_active', 'mcp_alerts')
    op.drop_index('idx_mcp_metrics_action_timestamp', 'mcp_metrics')
    op.drop_index('idx_mcp_metrics_server_timestamp', 'mcp_metrics')
    
    # Drop tables
    op.drop_table('mcp_cache_metrics')
    op.drop_table('mcp_alerts')
    op.drop_table('mcp_health_status')
    op.drop_table('mcp_metrics')
    
    print("✅ Dropped MCP monitoring tables")