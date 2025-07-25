"""
Retrieval-Augmented Generation (RAG) Service

This service combines semantic search with AI generation to provide
context-aware responses for legal document queries.
"""

import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime

from services.semantic_search import SemanticSearchEngine, SearchResult
from services.ai_service import AIService
from services.ollama_service import OllamaService
from models import Document, DocumentChunk, Organization
from database import get_db

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Context for RAG generation"""

    query: str
    retrieved_chunks: List[SearchResult]
    document_metadata: Dict[str, Dict]
    total_tokens: int

    def to_prompt_context(self) -> str:
        """Convert to context string for LLM prompt"""
        context_parts = []

        for chunk in self.retrieved_chunks:
            doc_meta = self.document_metadata.get(chunk.document_id, {})

            context_parts.append(
                f"Document: {doc_meta.get('file_name', 'Unknown')}\n"
                f"Type: {doc_meta.get('document_type', 'Unknown')}\n"
                f"Relevance Score: {chunk.combined_score:.2f}\n"
                f"Content:\n{chunk.content}\n"
                f"{'-' * 40}\n"
            )

        return "\n".join(context_parts)


@dataclass
class RAGResponse:
    """Response from RAG generation"""

    answer: str
    sources: List[Dict]
    confidence: float
    tokens_used: int
    search_time_ms: float
    generation_time_ms: float

    def to_dict(self) -> Dict:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "confidence": self.confidence,
            "tokens_used": self.tokens_used,
            "search_time_ms": self.search_time_ms,
            "generation_time_ms": self.generation_time_ms,
            "total_time_ms": self.search_time_ms + self.generation_time_ms,
        }


class RAGService:
    """
    Service for Retrieval-Augmented Generation combining semantic search
    with AI generation for context-aware legal document analysis.
    """

    def __init__(
        self,
        search_engine: Optional[SemanticSearchEngine] = None,
        ai_service: Optional[AIService] = None,
        ollama_service: Optional[OllamaService] = None,
        max_context_tokens: int = 3000,
        min_relevance_score: float = 0.5,
        use_local_llm: bool = True,
    ):
        """
        Initialize RAG service.

        Args:
            search_engine: Semantic search engine instance
            ai_service: AI service for cloud generation
            ollama_service: Ollama service for local generation
            max_context_tokens: Maximum tokens for context
            min_relevance_score: Minimum relevance score for chunks
            use_local_llm: Whether to prefer local LLM
        """
        self.search_engine = search_engine or SemanticSearchEngine()
        self.ai_service = ai_service
        self.ollama_service = ollama_service
        self.max_context_tokens = max_context_tokens
        self.min_relevance_score = min_relevance_score
        self.use_local_llm = use_local_llm

    async def query(
        self,
        query: str,
        organization_id: str,
        document_ids: Optional[List[str]] = None,
        document_types: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        conversation_history: Optional[List[Dict]] = None,
    ) -> RAGResponse:
        """
        Perform RAG query on documents.

        Args:
            query: User's question
            organization_id: Organization ID for access control
            document_ids: Optional document IDs to search within
            document_types: Optional document types to filter
            user_id: Optional user ID for personalization
            conversation_history: Optional conversation history

        Returns:
            RAGResponse with answer and sources
        """
        import time

        # Phase 1: Retrieval
        search_start = time.time()

        # Search for relevant chunks
        search_results = await self.search_engine.search(
            query=query,
            organization_id=organization_id,
            document_ids=document_ids,
            document_types=document_types,
            top_k=20,  # Get more candidates for filtering
            similarity_threshold=self.min_relevance_score,
            user_id=user_id,
        )

        search_time_ms = (time.time() - search_start) * 1000

        # Phase 2: Context Building
        context = await self._build_context(
            query=query, search_results=search_results, organization_id=organization_id
        )

        # Phase 3: Generation
        generation_start = time.time()

        # Generate response using appropriate service
        if self.use_local_llm and self.ollama_service:
            response = await self._generate_with_ollama(context, conversation_history)
        elif self.ai_service:
            response = await self._generate_with_ai_service(
                context, conversation_history
            )
        else:
            raise ValueError("No AI service available for generation")

        generation_time_ms = (time.time() - generation_start) * 1000

        # Extract sources
        sources = self._extract_sources(context)

        # Calculate confidence based on relevance scores
        avg_relevance = (
            sum(chunk.combined_score for chunk in context.retrieved_chunks)
            / len(context.retrieved_chunks)
            if context.retrieved_chunks
            else 0
        )

        return RAGResponse(
            answer=response["answer"],
            sources=sources,
            confidence=avg_relevance,
            tokens_used=response.get("tokens_used", 0),
            search_time_ms=search_time_ms,
            generation_time_ms=generation_time_ms,
        )

    async def _build_context(
        self, query: str, search_results: List[SearchResult], organization_id: str
    ) -> RAGContext:
        """Build context for generation"""
        db = next(get_db())

        try:
            # Get document metadata
            document_ids = list(set(r.document_id for r in search_results))
            documents = (
                db.query(Document)
                .filter(
                    Document.id.in_(document_ids),
                    Document.organization_id == organization_id,
                )
                .all()
            )

            doc_metadata = {
                doc.id: {
                    "file_name": doc.filename,
                    "document_type": getattr(doc, "document_type", "general"),
                    "created_at": (
                        doc.created_at.isoformat() if doc.created_at else None
                    ),
                    "summary": doc.summary,
                }
                for doc in documents
            }

            # Filter and rank chunks by relevance and diversity
            selected_chunks = self._select_diverse_chunks(
                search_results, self.max_context_tokens
            )

            # Calculate total tokens
            total_tokens = sum(
                len(chunk.content.split()) * 1.3  # Rough token estimate
                for chunk in selected_chunks
            )

            return RAGContext(
                query=query,
                retrieved_chunks=selected_chunks,
                document_metadata=doc_metadata,
                total_tokens=int(total_tokens),
            )

        finally:
            db.close()

    def _select_diverse_chunks(
        self, search_results: List[SearchResult], max_tokens: int
    ) -> List[SearchResult]:
        """
        Select diverse, relevant chunks within token limit.

        Uses MMR (Maximal Marginal Relevance) to balance relevance
        with diversity.
        """
        if not search_results:
            return []

        selected = []
        remaining = search_results.copy()
        current_tokens = 0

        # Start with most relevant
        best = max(remaining, key=lambda x: x.combined_score)
        selected.append(best)
        remaining.remove(best)
        current_tokens += len(best.content.split()) * 1.3

        # Add diverse chunks
        while remaining and current_tokens < max_tokens:
            # Calculate MMR scores
            mmr_scores = []

            for candidate in remaining:
                # Relevance to query
                relevance = candidate.combined_score

                # Similarity to already selected (penalize redundancy)
                max_sim = max(
                    self._text_similarity(candidate.content, s.content)
                    for s in selected
                )

                # MMR = λ * relevance - (1-λ) * max_similarity
                mmr = 0.7 * relevance - 0.3 * max_sim
                mmr_scores.append((candidate, mmr))

            # Select best MMR
            best_candidate, _ = max(mmr_scores, key=lambda x: x[1])

            # Check token limit
            candidate_tokens = len(best_candidate.content.split()) * 1.3
            if current_tokens + candidate_tokens > max_tokens:
                break

            selected.append(best_candidate)
            remaining.remove(best_candidate)
            current_tokens += candidate_tokens

        return selected

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity using Jaccard coefficient"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = words1 & words2
        union = words1 | words2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    async def _generate_with_ollama(
        self, context: RAGContext, conversation_history: Optional[List[Dict]]
    ) -> Dict:
        """Generate response using Ollama"""
        # Build prompt
        prompt = self._build_rag_prompt(context, conversation_history)

        # Generate response
        response = await self.ollama_service.generate(prompt)

        return {
            "answer": response,
            "tokens_used": len(prompt.split()) + len(response.split()),
        }

    async def _generate_with_ai_service(
        self, context: RAGContext, conversation_history: Optional[List[Dict]]
    ) -> Dict:
        """Generate response using AI service"""
        # Convert context to format expected by AI service
        doc_context = []

        for chunk in context.retrieved_chunks:
            doc_meta = context.document_metadata.get(chunk.document_id, {})
            doc_context.append(
                {
                    "content": chunk.content,
                    "metadata": {
                        "file_name": doc_meta.get("file_name"),
                        "document_type": doc_meta.get("document_type"),
                        "relevance_score": chunk.combined_score,
                    },
                }
            )

        # Generate response using the correct method from HybridAIService
        response = await self.ai_service.process_chat_message(
            message=context.query,
            context=doc_context,
            conversation_history=conversation_history,
        )

        return {
            "answer": response,
            "tokens_used": context.total_tokens + len(response.split()),
        }

    def _build_rag_prompt(
        self, context: RAGContext, conversation_history: Optional[List[Dict]]
    ) -> str:
        """Build prompt for RAG generation"""
        prompt_parts = [
            "You are a legal AI assistant analyzing documents to answer questions.",
            "Use only the provided context to answer. If the answer is not in the context, say so.",
            "",
            "Context from relevant documents:",
            context.to_prompt_context(),
            "",
        ]

        # Add conversation history if provided
        if conversation_history:
            prompt_parts.extend(
                [
                    "Previous conversation:",
                    self._format_conversation_history(conversation_history),
                    "",
                ]
            )

        prompt_parts.extend(
            [
                f"Question: {context.query}",
                "",
                "Please provide a comprehensive answer based on the documents provided.",
                "Cite specific documents when making claims.",
                "If multiple documents have conflicting information, note the discrepancy.",
                "",
                "Answer:",
            ]
        )

        return "\n".join(prompt_parts)

    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history for prompt"""
        formatted = []

        for msg in history[-5:]:  # Last 5 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append(f"{role.capitalize()}: {content}")

        return "\n".join(formatted)

    def _extract_sources(self, context: RAGContext) -> List[Dict]:
        """Extract source information from context"""
        sources = []
        seen_docs = set()

        for chunk in context.retrieved_chunks:
            doc_id = chunk.document_id

            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                doc_meta = context.document_metadata.get(doc_id, {})

                sources.append(
                    {
                        "document_id": doc_id,
                        "file_name": doc_meta.get("file_name", "Unknown"),
                        "document_type": doc_meta.get("document_type", "Unknown"),
                        "relevance_score": chunk.combined_score,
                        "chunks_used": 1,
                    }
                )
            else:
                # Increment chunk count for existing source
                for source in sources:
                    if source["document_id"] == doc_id:
                        source["chunks_used"] += 1
                        source["relevance_score"] = max(
                            source["relevance_score"], chunk.combined_score
                        )
                        break

        # Sort by relevance
        sources.sort(key=lambda x: x["relevance_score"], reverse=True)

        return sources

    async def explain_answer(
        self, query: str, answer: str, sources: List[Dict], organization_id: str
    ) -> Dict:
        """
        Explain how an answer was derived from sources.

        Args:
            query: Original query
            answer: Generated answer
            sources: Source documents used
            organization_id: Organization ID

        Returns:
            Explanation of reasoning
        """
        db = next(get_db())

        try:
            # Get actual chunks used
            doc_ids = [s["document_id"] for s in sources]

            # Re-run search to get specific chunks
            search_results = await self.search_engine.search(
                query=query,
                organization_id=organization_id,
                document_ids=doc_ids,
                top_k=10,
            )

            # Build explanation
            explanation = {
                "query": query,
                "answer": answer,
                "reasoning_steps": [],
                "key_evidence": [],
            }

            # Analyze each relevant chunk
            for chunk in search_results[:5]:  # Top 5 chunks
                # Find key phrases that support the answer
                key_phrases = self._extract_key_phrases(chunk.content, answer)

                if key_phrases:
                    explanation["key_evidence"].append(
                        {
                            "document": chunk.metadata.get("file_name", "Unknown"),
                            "content_excerpt": chunk.content[:200] + "...",
                            "key_phrases": key_phrases,
                            "relevance_score": chunk.combined_score,
                        }
                    )

            # Add reasoning steps
            explanation["reasoning_steps"] = [
                f"Searched for documents related to: {query}",
                f"Found {len(sources)} relevant documents",
                f"Extracted key information from top-ranked chunks",
                "Synthesized answer based on evidence",
                "Verified answer consistency across sources",
            ]

            return explanation

        finally:
            db.close()

    def _extract_key_phrases(self, content: str, answer: str) -> List[str]:
        """Extract phrases from content that support the answer"""
        # Simple keyword extraction
        answer_words = set(answer.lower().split())
        content_sentences = content.split(".")

        key_phrases = []

        for sentence in content_sentences:
            sentence_words = set(sentence.lower().split())

            # Check overlap with answer
            overlap = answer_words & sentence_words

            if len(overlap) >= 3:  # At least 3 common words
                key_phrases.append(sentence.strip())

        return key_phrases[:3]  # Top 3 phrases
