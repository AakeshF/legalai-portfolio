"""
Semantic Search Engine for Legal Documents

This service implements hybrid search combining vector similarity search
with traditional keyword search for optimal legal document retrieval.
"""

import hashlib
import asyncio
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy import text, and_, or_
from sqlalchemy.orm import Session
import logging

from models import (
    Document, DocumentChunk, ChunkEmbedding, SearchCache,
    EmbeddingModel, Organization
)
from services.embedding_service import EmbeddingService, get_embedding_service
from database import get_db

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a search result with metadata"""
    chunk_id: str
    document_id: str
    content: str
    similarity_score: float
    keyword_score: float
    combined_score: float
    metadata: Dict
    
    def to_dict(self) -> Dict:
        return {
            'chunk_id': self.chunk_id,
            'document_id': self.document_id,
            'content': self.content,
            'similarity_score': self.similarity_score,
            'keyword_score': self.keyword_score,
            'combined_score': self.combined_score,
            'metadata': self.metadata
        }


class SemanticSearchEngine:
    """
    Hybrid search engine combining semantic vector search with keyword search
    for comprehensive legal document retrieval.
    """
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        cache_ttl_hours: int = 24,
        use_cache: bool = True
    ):
        """
        Initialize the search engine.
        
        Args:
            embedding_service: Service for generating embeddings
            vector_weight: Weight for vector similarity (0-1)
            keyword_weight: Weight for keyword matching (0-1)
            cache_ttl_hours: Cache time-to-live in hours
            use_cache: Whether to use search result caching
        """
        self.embedding_service = embedding_service or get_embedding_service()
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.cache_ttl_hours = cache_ttl_hours
        self.use_cache = use_cache
        
        # Ensure weights sum to 1
        total_weight = vector_weight + keyword_weight
        if total_weight != 1.0:
            self.vector_weight = vector_weight / total_weight
            self.keyword_weight = keyword_weight / total_weight
            
    async def search(
        self,
        query: str,
        organization_id: str,
        document_ids: Optional[List[str]] = None,
        document_types: Optional[List[str]] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
        user_id: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search on documents.
        
        Args:
            query: Search query text
            organization_id: Organization ID for access control
            document_ids: Optional list of document IDs to search within
            document_types: Optional list of document types to filter
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score
            user_id: Optional user ID for personalization
            
        Returns:
            List of SearchResult objects
        """
        # Check cache first
        if self.use_cache:
            cached_results = await self._check_cache(
                query, organization_id, document_ids, document_types
            )
            if cached_results:
                return cached_results
                
        # Generate query embedding
        query_embedding_result = await self.embedding_service.generate_embedding(query)
        query_embedding = query_embedding_result.embedding
        
        # Get database session
        db = next(get_db())
        
        try:
            # Perform vector search
            vector_results = await self._vector_search(
                db,
                query_embedding,
                organization_id,
                document_ids,
                document_types,
                top_k * 2  # Get more candidates for re-ranking
            )
            
            # Perform keyword search
            keyword_results = await self._keyword_search(
                db,
                query,
                organization_id,
                document_ids,
                document_types,
                top_k * 2
            )
            
            # Combine and re-rank results
            final_results = self._combine_results(
                vector_results,
                keyword_results,
                similarity_threshold,
                top_k
            )
            
            # Cache results
            if self.use_cache:
                await self._cache_results(
                    query,
                    query_embedding,
                    organization_id,
                    document_ids,
                    document_types,
                    final_results
                )
                
            return final_results
            
        finally:
            db.close()
            
    async def _vector_search(
        self,
        db: Session,
        query_embedding: List[float],
        organization_id: str,
        document_ids: Optional[List[str]],
        document_types: Optional[List[str]],
        limit: int
    ) -> List[Tuple[str, float, Dict]]:
        """
        Perform vector similarity search using pgvector.
        
        Returns list of (chunk_id, similarity_score, metadata) tuples.
        """
        # Build the query
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Base query with vector similarity
        query = """
            SELECT 
                c.id as chunk_id,
                c.document_id,
                c.content,
                c.chunk_metadata,
                d.filename,
                1 - (e.embedding <=> :query_embedding::vector) as similarity
            FROM chunk_embeddings e
            JOIN document_chunks c ON e.chunk_id = c.id
            JOIN documents d ON c.document_id = d.id
            WHERE d.organization_id = :org_id
        """
        
        params = {
            'query_embedding': embedding_str,
            'org_id': organization_id
        }
        
        # Add filters
        if document_ids:
            query += " AND d.id IN :doc_ids"
            params['doc_ids'] = tuple(document_ids)
            
        if document_types:
            query += " AND d.document_type IN :doc_types"
            params['doc_types'] = tuple(document_types)
            
        # Order by similarity and limit
        query += " ORDER BY similarity DESC LIMIT :limit"
        params['limit'] = limit
        
        # Execute query
        result = db.execute(text(query), params)
        
        vector_results = []
        for row in result:
            metadata = {
                'document_id': row.document_id,
                'file_name': row.filename,
                'document_type': row.content_type or 'general',
                'chunk_metadata': row.chunk_metadata or {}
            }
            vector_results.append((
                row.chunk_id,
                row.content,
                row.similarity,
                metadata
            ))
            
        return vector_results
        
    async def _keyword_search(
        self,
        db: Session,
        query: str,
        organization_id: str,
        document_ids: Optional[List[str]],
        document_types: Optional[List[str]],
        limit: int
    ) -> List[Tuple[str, float, Dict]]:
        """
        Perform keyword-based full-text search.
        
        Returns list of (chunk_id, keyword_score, metadata) tuples.
        """
        # Prepare search terms
        search_terms = query.lower().split()
        
        # Build query conditions
        chunk_query = db.query(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.document_id,
            DocumentChunk.chunk_metadata,
            Document.filename,
            Document.content_type
        ).join(
            Document, DocumentChunk.document_id == Document.id
        ).filter(
            Document.organization_id == organization_id
        )
        
        # Add filters
        if document_ids:
            chunk_query = chunk_query.filter(Document.id.in_(document_ids))
            
        if document_types:
            chunk_query = chunk_query.filter(Document.document_type.in_(document_types))
            
        # Add keyword search conditions
        search_conditions = []
        for term in search_terms:
            search_conditions.append(
                DocumentChunk.content.ilike(f'%{term}%')
            )
            
        if search_conditions:
            chunk_query = chunk_query.filter(or_(*search_conditions))
            
        # Execute query
        results = chunk_query.limit(limit).all()
        
        keyword_results = []
        for chunk in results:
            # Calculate keyword score based on term frequency
            content_lower = chunk.content.lower()
            matches = sum(
                content_lower.count(term) for term in search_terms
            )
            keyword_score = min(1.0, matches / len(search_terms) / 10)
            
            metadata = {
                'document_id': chunk.document_id,
                'file_name': chunk.filename,
                'document_type': chunk.content_type or 'general',
                'chunk_metadata': chunk.chunk_metadata or {}
            }
            
            keyword_results.append((
                chunk.id,
                chunk.content,
                keyword_score,
                metadata
            ))
            
        return keyword_results
        
    def _combine_results(
        self,
        vector_results: List[Tuple[str, str, float, Dict]],
        keyword_results: List[Tuple[str, str, float, Dict]],
        similarity_threshold: float,
        top_k: int
    ) -> List[SearchResult]:
        """
        Combine vector and keyword search results with re-ranking.
        """
        # Create dictionaries for easy lookup
        vector_dict = {
            chunk_id: (content, score, metadata)
            for chunk_id, content, score, metadata in vector_results
        }
        
        keyword_dict = {
            chunk_id: (content, score, metadata)
            for chunk_id, content, score, metadata in keyword_results
        }
        
        # Combine all unique chunk IDs
        all_chunk_ids = set(vector_dict.keys()) | set(keyword_dict.keys())
        
        combined_results = []
        
        for chunk_id in all_chunk_ids:
            # Get scores (default to 0 if not found)
            vector_score = vector_dict.get(chunk_id, (None, 0, {}))[1]
            keyword_score = keyword_dict.get(chunk_id, (None, 0, {}))[1]
            
            # Skip if below similarity threshold
            if vector_score < similarity_threshold:
                continue
                
            # Get content and metadata (prefer from vector results)
            if chunk_id in vector_dict:
                content, _, metadata = vector_dict[chunk_id]
            else:
                content, _, metadata = keyword_dict[chunk_id]
                
            # Calculate combined score
            combined_score = (
                self.vector_weight * vector_score +
                self.keyword_weight * keyword_score
            )
            
            result = SearchResult(
                chunk_id=chunk_id,
                document_id=metadata['document_id'],
                content=content,
                similarity_score=vector_score,
                keyword_score=keyword_score,
                combined_score=combined_score,
                metadata=metadata
            )
            
            combined_results.append(result)
            
        # Sort by combined score
        combined_results.sort(key=lambda x: x.combined_score, reverse=True)
        
        return combined_results[:top_k]
        
    async def _check_cache(
        self,
        query: str,
        organization_id: str,
        document_ids: Optional[List[str]],
        document_types: Optional[List[str]]
    ) -> Optional[List[SearchResult]]:
        """Check if results are cached"""
        db = next(get_db())
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(
                query, organization_id, document_ids, document_types
            )
            
            # Look up in cache
            cache_entry = db.query(SearchCache).filter(
                SearchCache.query_hash == cache_key,
                SearchCache.organization_id == organization_id,
                SearchCache.expires_at > datetime.utcnow()
            ).first()
            
            if not cache_entry:
                return None
                
            # Update hit count
            cache_entry.hit_count += 1
            cache_entry.last_accessed = datetime.utcnow()
            db.commit()
            
            # Reconstruct results
            results = []
            for i, chunk_id in enumerate(cache_entry.result_chunk_ids):
                # Get chunk details
                chunk = db.query(DocumentChunk).filter(
                    DocumentChunk.id == chunk_id
                ).first()
                
                if chunk:
                    result = SearchResult(
                        chunk_id=chunk_id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        similarity_score=cache_entry.result_scores[i],
                        keyword_score=0,  # Not stored in cache
                        combined_score=cache_entry.result_scores[i],
                        metadata={'cached': True}
                    )
                    results.append(result)
                    
            return results
            
        finally:
            db.close()
            
    async def _cache_results(
        self,
        query: str,
        query_embedding: List[float],
        organization_id: str,
        document_ids: Optional[List[str]],
        document_types: Optional[List[str]],
        results: List[SearchResult]
    ):
        """Cache search results"""
        db = next(get_db())
        
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(
                query, organization_id, document_ids, document_types
            )
            
            # Create cache entry
            cache_entry = SearchCache(
                query_hash=cache_key,
                query_text=query,
                query_embedding=query_embedding,
                result_chunk_ids=[r.chunk_id for r in results],
                result_scores=[r.combined_score for r in results],
                organization_id=organization_id,
                expires_at=datetime.utcnow() + timedelta(hours=self.cache_ttl_hours)
            )
            
            db.add(cache_entry)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to cache results: {e}")
            db.rollback()
        finally:
            db.close()
            
    def _generate_cache_key(
        self,
        query: str,
        organization_id: str,
        document_ids: Optional[List[str]],
        document_types: Optional[List[str]]
    ) -> str:
        """Generate deterministic cache key"""
        key_parts = [query, organization_id]
        
        if document_ids:
            key_parts.extend(sorted(document_ids))
            
        if document_types:
            key_parts.extend(sorted(document_types))
            
        key_string = '|'.join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
        
    async def find_similar_documents(
        self,
        document_id: str,
        organization_id: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find documents similar to a given document.
        
        Args:
            document_id: Source document ID
            organization_id: Organization ID for access control
            top_k: Number of similar documents to return
            
        Returns:
            List of similar documents with scores
        """
        db = next(get_db())
        
        try:
            # Get embeddings for the source document
            source_embeddings = db.query(ChunkEmbedding).join(
                DocumentChunk
            ).filter(
                DocumentChunk.document_id == document_id
            ).all()
            
            if not source_embeddings:
                return []
                
            # Average embeddings for document representation
            embeddings_array = np.array([e.embedding for e in source_embeddings])
            doc_embedding = np.mean(embeddings_array, axis=0)
            
            # Search for similar documents
            results = await self._vector_search(
                db,
                doc_embedding.tolist(),
                organization_id,
                None,  # Search all documents
                None,
                top_k * 3  # Get more candidates
            )
            
            # Group by document and aggregate scores
            doc_scores = {}
            for chunk_id, content, score, metadata in results:
                doc_id = metadata['document_id']
                if doc_id == document_id:
                    continue  # Skip source document
                    
                if doc_id not in doc_scores:
                    doc_scores[doc_id] = {
                        'document_id': doc_id,
                        'file_name': metadata['file_name'],
                        'document_type': metadata['document_type'],
                        'max_score': score,
                        'avg_score': score,
                        'match_count': 1
                    }
                else:
                    doc_scores[doc_id]['max_score'] = max(
                        doc_scores[doc_id]['max_score'], score
                    )
                    doc_scores[doc_id]['avg_score'] = (
                        (doc_scores[doc_id]['avg_score'] * doc_scores[doc_id]['match_count'] + score) /
                        (doc_scores[doc_id]['match_count'] + 1)
                    )
                    doc_scores[doc_id]['match_count'] += 1
                    
            # Sort by average score
            similar_docs = sorted(
                doc_scores.values(),
                key=lambda x: x['avg_score'],
                reverse=True
            )
            
            return similar_docs[:top_k]
            
        finally:
            db.close()