#!/usr/bin/env python3
"""Fix vector search schema mismatches"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from config import settings


def fix_schema():
    """Fix vector search schema issues"""

    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        # Add missing columns to search_cache
        try:
            conn.execute(text("ALTER TABLE search_cache ADD COLUMN user_id TEXT"))
            conn.execute(
                text("ALTER TABLE search_cache ADD COLUMN hit_count INTEGER DEFAULT 0")
            )
            conn.execute(
                text("ALTER TABLE search_cache ADD COLUMN last_accessed TIMESTAMP")
            )
            print("✅ Added missing columns to search_cache")
        except Exception as e:
            print(f"⚠️  search_cache columns may already exist: {e}")

        # Add missing columns to embedding_models
        try:
            conn.execute(
                text("ALTER TABLE embedding_models ADD COLUMN model_config TEXT")
            )
            conn.execute(
                text(
                    "ALTER TABLE embedding_models ADD COLUMN avg_encoding_time_ms REAL"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE embedding_models ADD COLUMN total_documents_encoded INTEGER DEFAULT 0"
                )
            )
            print("✅ Added missing columns to embedding_models")
        except Exception as e:
            print(f"⚠️  embedding_models columns may already exist: {e}")

        # Add missing columns to chunk_embeddings
        try:
            conn.execute(
                text("ALTER TABLE chunk_embeddings ADD COLUMN encoding_time_ms REAL")
            )
            print("✅ Added encoding_time_ms to chunk_embeddings")
        except Exception as e:
            print(f"⚠️  chunk_embeddings columns may already exist: {e}")

        conn.commit()

    print("\n✅ Schema fixes applied!")


if __name__ == "__main__":
    fix_schema()
