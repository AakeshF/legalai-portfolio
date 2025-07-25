"""
SQLite-compatible Semantic Search Engine

This is a simplified version that works with SQLite by computing
cosine similarity in Python instead of using pgvector.
"""

import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from models import Document, DocumentChunk, ChunkEmbedding
from services.semantic_search import SearchResult, SemanticSearchEngine


class SQLiteSemanticSearchEngine(SemanticSearchEngine):
    """SQLite-compatible semantic search engine"""

    async def _vector_search(
        self,
        db: Session,
        query_embedding: List[float],
        organization_id: str,
        document_ids: Optional[List[str]],
        document_types: Optional[List[str]],
        limit: int,
    ) -> List[Tuple[str, float, Dict]]:
        """
        Perform vector similarity search for SQLite.
        Computes cosine similarity in Python.
        """
        # Build base query
        query = (
            db.query(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.content,
                DocumentChunk.chunk_metadata,
                Document.filename,
                ChunkEmbedding.embedding,
            )
            .join(ChunkEmbedding, DocumentChunk.id == ChunkEmbedding.chunk_id)
            .join(Document, DocumentChunk.document_id == Document.id)
            .filter(Document.organization_id == organization_id)
        )

        # Add filters
        if document_ids:
            query = query.filter(Document.id.in_(document_ids))

        # Execute query
        results = query.all()

        # Compute similarities in Python
        query_vec = np.array(query_embedding)
        scored_results = []

        for row in results:
            # Parse embedding from JSON string
            if isinstance(row.embedding, str):
                chunk_embedding = np.array(json.loads(row.embedding))
            else:
                chunk_embedding = np.array(row.embedding)

            # Compute cosine similarity
            similarity = np.dot(query_vec, chunk_embedding) / (
                np.linalg.norm(query_vec) * np.linalg.norm(chunk_embedding)
            )

            metadata = {
                "document_id": row.document_id,
                "file_name": row.filename,
                "document_type": "general",
                "chunk_metadata": row.chunk_metadata or {},
            }

            scored_results.append((row.id, row.content, float(similarity), metadata))

        # Sort by similarity and limit
        scored_results.sort(key=lambda x: x[2], reverse=True)
        return scored_results[:limit]
