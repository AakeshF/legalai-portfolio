"""Add vector search tables for semantic search and RAG

This migration adds support for pgvector and creates tables for storing
document embeddings and chunks for semantic search capabilities.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime

# Revision identifiers
revision = 'add_vector_search'
down_revision = 'add_user_ai_preferences'
branch_labels = None
depends_on = None


def upgrade():
    """Add vector search tables and pgvector extension"""
    
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create embedding models table
    op.create_table(
        'embedding_models',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),  # e.g., 'legal-bert-base'
        sa.Column('dimension', sa.Integer(), nullable=False),  # e.g., 768
        sa.Column('provider', sa.String(), nullable=False),  # 'local' or 'openai'
        sa.Column('description', sa.Text()),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('is_active', sa.Boolean(), default=True)
    )
    
    # Create document chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('document_id', sa.String(), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),  # Order within document
        sa.Column('content', sa.Text(), nullable=False),  # Actual text content
        sa.Column('tokens', sa.Integer()),  # Token count
        sa.Column('start_char', sa.Integer()),  # Character position in original
        sa.Column('end_char', sa.Integer()),
        sa.Column('chunk_metadata', sa.JSON()),  # Section info, headers, etc.
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow)
    )
    
    # Create chunk embeddings table with vector column
    op.create_table(
        'chunk_embeddings',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('chunk_id', sa.String(), sa.ForeignKey('document_chunks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model_id', sa.String(), sa.ForeignKey('embedding_models.id'), nullable=False),
        sa.Column('embedding', postgresql.ARRAY(sa.Float), nullable=False),  # Vector storage
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow)
    )
    
    # Create semantic search cache table
    op.create_table(
        'search_cache',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('query_hash', sa.String(), nullable=False, unique=True),
        sa.Column('query_text', sa.Text(), nullable=False),
        sa.Column('query_embedding', postgresql.ARRAY(sa.Float)),
        sa.Column('result_chunk_ids', postgresql.ARRAY(sa.String)),
        sa.Column('result_scores', postgresql.ARRAY(sa.Float)),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id')),
        sa.Column('created_at', sa.DateTime(), default=datetime.utcnow),
        sa.Column('expires_at', sa.DateTime())
    )
    
    # Add vector indices for similarity search
    op.execute('''
        CREATE INDEX idx_chunk_embeddings_vector 
        ON chunk_embeddings 
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    ''')
    
    # Add composite indices for performance
    op.create_index('idx_document_chunks_doc_id', 'document_chunks', ['document_id'])
    op.create_index('idx_document_chunks_order', 'document_chunks', ['document_id', 'chunk_index'])
    op.create_index('idx_chunk_embeddings_chunk', 'chunk_embeddings', ['chunk_id'])
    op.create_index('idx_search_cache_org', 'search_cache', ['organization_id', 'query_hash'])
    
    # Add columns to existing documents table for RAG status
    op.add_column('documents', sa.Column('chunks_generated', sa.Boolean(), default=False))
    op.add_column('documents', sa.Column('embeddings_generated', sa.Boolean(), default=False))
    op.add_column('documents', sa.Column('embedding_model_id', sa.String()))
    op.add_column('documents', sa.Column('chunk_count', sa.Integer(), default=0))
    op.add_column('documents', sa.Column('last_embedded_at', sa.DateTime()))


def downgrade():
    """Remove vector search tables"""
    
    # Remove columns from documents table
    op.drop_column('documents', 'last_embedded_at')
    op.drop_column('documents', 'chunk_count')
    op.drop_column('documents', 'embedding_model_id')
    op.drop_column('documents', 'embeddings_generated')
    op.drop_column('documents', 'chunks_generated')
    
    # Drop indices
    op.drop_index('idx_search_cache_org')
    op.drop_index('idx_chunk_embeddings_chunk')
    op.drop_index('idx_document_chunks_order')
    op.drop_index('idx_document_chunks_doc_id')
    op.drop_index('idx_chunk_embeddings_vector')
    
    # Drop tables
    op.drop_table('search_cache')
    op.drop_table('chunk_embeddings')
    op.drop_table('document_chunks')
    op.drop_table('embedding_models')
    
    # Disable pgvector extension (optional, might affect other uses)
    # op.execute('DROP EXTENSION IF EXISTS vector')