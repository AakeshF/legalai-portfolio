#!/usr/bin/env python3
"""
Manual migration script for vector search tables that works with SQLite
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from config import settings
import json

def run_migration():
    """Run vector search migration for SQLite"""
    
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Create embedding models table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS embedding_models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                dimension INTEGER NOT NULL,
                provider TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """))
        
        # Create document chunks table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                tokens INTEGER,
                start_char INTEGER,
                end_char INTEGER,
                chunk_metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                embedding_generated BOOLEAN DEFAULT 0,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """))
        
        # Create chunk embeddings table (store embeddings as JSON in SQLite)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chunk_embeddings (
                id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL,
                model_id TEXT NOT NULL,
                embedding TEXT NOT NULL,
                encoding_time_ms REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chunk_id) REFERENCES document_chunks(id) ON DELETE CASCADE,
                FOREIGN KEY (model_id) REFERENCES embedding_models(id)
            )
        """))
        
        # Create search cache table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS search_cache (
                id TEXT PRIMARY KEY,
                query_hash TEXT NOT NULL UNIQUE,
                query_text TEXT NOT NULL,
                query_embedding TEXT,
                result_chunk_ids TEXT,
                result_scores TEXT,
                organization_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id)
            )
        """))
        
        # Create indices
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_id ON document_chunks(document_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_document_chunks_order ON document_chunks(document_id, chunk_index)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_chunk ON chunk_embeddings(chunk_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_search_cache_org ON search_cache(organization_id, query_hash)"))
        
        # Add columns to documents table
        try:
            conn.execute(text("ALTER TABLE documents ADD COLUMN chunks_generated BOOLEAN DEFAULT 0"))
        except:
            pass  # Column may already exist
            
        try:
            conn.execute(text("ALTER TABLE documents ADD COLUMN embeddings_generated BOOLEAN DEFAULT 0"))
        except:
            pass
            
        try:
            conn.execute(text("ALTER TABLE documents ADD COLUMN embedding_model_id TEXT"))
        except:
            pass
            
        try:
            conn.execute(text("ALTER TABLE documents ADD COLUMN chunk_count INTEGER DEFAULT 0"))
        except:
            pass
            
        try:
            conn.execute(text("ALTER TABLE documents ADD COLUMN last_embedded_at TIMESTAMP"))
        except:
            pass
        
        # Insert default embedding model
        conn.execute(text("""
            INSERT OR IGNORE INTO embedding_models (id, name, dimension, provider, description, is_active)
            VALUES ('all-minilm-l6-v2', 'all-MiniLM-L6-v2', 384, 'local', 'Sentence-transformers model for semantic search', 1)
        """))
        
        conn.commit()
        
    print("✅ Vector search tables created successfully!")

if __name__ == "__main__":
    run_migration()