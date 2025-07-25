"""
Embedding Service for Semantic Search

This service generates embeddings for text using sentence-transformers
for local processing or external APIs for enhanced accuracy.
"""

import time
import hashlib
import numpy as np
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Local embedding libraries
from sentence_transformers import SentenceTransformer
import torch

# For external providers
import httpx

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation"""

    embedding: List[float]
    model_name: str
    dimension: int
    encoding_time_ms: float
    tokens_used: Optional[int] = None


class EmbeddingService:
    """
    Service for generating text embeddings with support for multiple providers
    and models optimized for legal text.
    """

    # Available models with their configurations
    MODELS = {
        "local": {
            "all-MiniLM-L6-v2": {
                "dimension": 384,
                "max_tokens": 256,
                "description": "Fast, general-purpose model",
            },
            "all-mpnet-base-v2": {
                "dimension": 768,
                "max_tokens": 384,
                "description": "Higher quality, general-purpose",
            },
            "legal-bert-base-uncased": {
                "dimension": 768,
                "max_tokens": 512,
                "description": "Fine-tuned on legal text",
            },
            "multi-qa-MiniLM-L6-cos-v1": {
                "dimension": 384,
                "max_tokens": 512,
                "description": "Optimized for question-answering",
            },
        },
        "openai": {
            "text-embedding-ada-002": {
                "dimension": 1536,
                "max_tokens": 8191,
                "description": "OpenAI's latest embedding model",
            }
        },
    }

    def __init__(
        self,
        model_name: str = "all-mpnet-base-v2",
        provider: str = "local",
        cache_embeddings: bool = True,
        batch_size: int = 32,
    ):
        """
        Initialize the embedding service.

        Args:
            model_name: Name of the model to use
            provider: Provider to use ('local' or 'openai')
            cache_embeddings: Whether to cache generated embeddings
            batch_size: Batch size for processing multiple texts
        """
        self.model_name = model_name
        self.provider = provider
        self.cache_embeddings = cache_embeddings
        self.batch_size = batch_size
        self.cache = {} if cache_embeddings else None

        # Initialize model based on provider
        if provider == "local":
            self._init_local_model()
        else:
            self._init_external_provider()

        # Get model configuration
        self.model_config = self.MODELS[provider][model_name]
        self.dimension = self.model_config["dimension"]
        self.max_tokens = self.model_config["max_tokens"]

        # Thread pool for CPU-bound embedding generation
        self.executor = ThreadPoolExecutor(max_workers=4)

    def _init_local_model(self):
        """Initialize local sentence-transformer model"""
        try:
            # Check if CUDA is available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device}")

            # Load model
            self.model = SentenceTransformer(self.model_name, device=device)

            # Enable multi-GPU if available
            if torch.cuda.device_count() > 1:
                logger.info(f"Using {torch.cuda.device_count()} GPUs")
                self.model = torch.nn.DataParallel(self.model)

        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            # Fallback to a basic model
            self.model_name = "all-MiniLM-L6-v2"
            self.model = SentenceTransformer(self.model_name)

    def _init_external_provider(self):
        """Initialize external API provider"""
        if self.provider == "openai":
            self.api_key = getattr(settings, "openai_api_key", None)
            self.api_url = "https://api.openai.com/v1/embeddings"
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    async def generate_embedding(
        self, text: str, metadata: Optional[Dict] = None
    ) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            metadata: Optional metadata for caching

        Returns:
            EmbeddingResult object
        """
        # Check cache
        if self.cache_embeddings:
            cache_key = self._get_cache_key(text, metadata)
            if cache_key in self.cache:
                return self.cache[cache_key]

        start_time = time.time()

        if self.provider == "local":
            embedding = await self._generate_local_embedding(text)
        else:
            embedding = await self._generate_external_embedding(text)

        encoding_time_ms = (time.time() - start_time) * 1000

        result = EmbeddingResult(
            embedding=(
                embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
            ),
            model_name=self.model_name,
            dimension=self.dimension,
            encoding_time_ms=encoding_time_ms,
        )

        # Cache result
        if self.cache_embeddings:
            self.cache[cache_key] = result

        return result

    async def generate_embeddings_batch(
        self, texts: List[str], metadata: Optional[List[Dict]] = None
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts efficiently.

        Args:
            texts: List of texts to embed
            metadata: Optional metadata for each text

        Returns:
            List of EmbeddingResult objects
        """
        if not texts:
            return []

        # Split into batches
        batches = [
            texts[i : i + self.batch_size]
            for i in range(0, len(texts), self.batch_size)
        ]

        results = []

        for batch_idx, batch in enumerate(batches):
            start_time = time.time()

            if self.provider == "local":
                embeddings = await self._generate_local_embeddings_batch(batch)
            else:
                embeddings = await self._generate_external_embeddings_batch(batch)

            encoding_time_ms = (time.time() - start_time) * 1000

            # Create results
            for i, (text, embedding) in enumerate(zip(batch, embeddings)):
                result = EmbeddingResult(
                    embedding=(
                        embedding.tolist()
                        if isinstance(embedding, np.ndarray)
                        else embedding
                    ),
                    model_name=self.model_name,
                    dimension=self.dimension,
                    encoding_time_ms=encoding_time_ms / len(batch),  # Average per text
                )
                results.append(result)

                # Cache if enabled
                if self.cache_embeddings and metadata:
                    meta_idx = batch_idx * self.batch_size + i
                    cache_key = self._get_cache_key(
                        text, metadata[meta_idx] if meta_idx < len(metadata) else None
                    )
                    self.cache[cache_key] = result

        return results

    async def _generate_local_embedding(self, text: str) -> np.ndarray:
        """Generate embedding using local model"""
        loop = asyncio.get_event_loop()

        # Truncate text if needed
        if len(text.split()) > self.max_tokens:
            text = " ".join(text.split()[: self.max_tokens])

        # Run in thread pool to avoid blocking
        embedding = await loop.run_in_executor(self.executor, self.model.encode, text)

        return embedding

    async def _generate_local_embeddings_batch(
        self, texts: List[str]
    ) -> List[np.ndarray]:
        """Generate embeddings for batch using local model"""
        loop = asyncio.get_event_loop()

        # Truncate texts if needed
        truncated_texts = []
        for text in texts:
            if len(text.split()) > self.max_tokens:
                text = " ".join(text.split()[: self.max_tokens])
            truncated_texts.append(text)

        # Run in thread pool
        embeddings = await loop.run_in_executor(
            self.executor, self.model.encode, truncated_texts
        )

        return embeddings

    async def _generate_external_embedding(self, text: str) -> List[float]:
        """Generate embedding using external API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model_name, "input": text},
            )

            if response.status_code != 200:
                raise Exception(f"API error: {response.text}")

            data = response.json()
            return data["data"][0]["embedding"]

    async def _generate_external_embeddings_batch(
        self, texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings for batch using external API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model_name, "input": texts},
            )

            if response.status_code != 200:
                raise Exception(f"API error: {response.text}")

            data = response.json()
            return [item["embedding"] for item in data["data"]]

    def _get_cache_key(self, text: str, metadata: Optional[Dict] = None) -> str:
        """Generate cache key for text and metadata"""
        key_parts = [text, self.model_name, self.provider]

        if metadata:
            # Add relevant metadata to key
            for k in sorted(metadata.keys()):
                key_parts.append(f"{k}:{metadata[k]}")

        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def calculate_similarity(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score between -1 and 1
        """
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        return float(similarity)

    def find_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 10,
        threshold: float = 0.0,
    ) -> List[Tuple[int, float]]:
        """
        Find most similar embeddings to a query.

        Args:
            query_embedding: Query embedding vector
            candidate_embeddings: List of candidate embeddings
            top_k: Number of top results to return
            threshold: Minimum similarity threshold

        Returns:
            List of (index, similarity_score) tuples
        """
        similarities = []

        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.calculate_similarity(query_embedding, candidate)
            if similarity >= threshold:
                similarities.append((i, similarity))

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]

    def get_model_info(self) -> Dict:
        """Get information about the current model"""
        return {
            "provider": self.provider,
            "model_name": self.model_name,
            "dimension": self.dimension,
            "max_tokens": self.max_tokens,
            "description": self.model_config["description"],
            "cache_enabled": self.cache_embeddings,
            "cache_size": len(self.cache) if self.cache else 0,
        }

    def clear_cache(self):
        """Clear the embedding cache"""
        if self.cache:
            self.cache.clear()
            logger.info("Embedding cache cleared")

    async def close(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True)
        if hasattr(self, "model") and hasattr(self.model, "close"):
            self.model.close()


# Singleton instance for easy access
_embedding_service = None


def get_embedding_service(
    model_name: Optional[str] = None, provider: Optional[str] = None
) -> EmbeddingService:
    """
    Get or create the embedding service singleton.

    Args:
        model_name: Override default model name
        provider: Override default provider

    Returns:
        EmbeddingService instance
    """
    global _embedding_service

    if _embedding_service is None or model_name or provider:
        _embedding_service = EmbeddingService(
            model_name=model_name or "all-mpnet-base-v2", provider=provider or "local"
        )

    return _embedding_service
