"""
Vector Database Retriever for ZhiYuQiao.

Manages Chroma vector database for semantic similarity search across
multiple knowledge domains (HSK, MUCGEC, teacher development, strategies, etc.)
"""

import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import OrderedDict
from datetime import datetime, timedelta

import chromadb
from sentence_transformers import SentenceTransformer

from .config import (
    EMBEDDING_BACKEND,
    EMBEDDING_MODEL,
    EMBEDDING_ONNX_FILE,
    VECTOR_DB_DIR,
)

logger = logging.getLogger(__name__)

# Constants
DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"
MAX_CONTEXT_CHARS = 3000
VECTOR_SEARCH_TOP_K = 5
CACHE_TTL_MINUTES = 60
CACHE_MAX_SIZE = 1000
VECTOR_DOMAINS = (
    "hsk",
    "mucgec",
    "teacher",
    "strategies",
    "references",
    "softwares",
    "haipai",
)


class VectorDB:
    """Singleton for managing Chroma vector database."""

    _instance = None
    _singleton_lock = threading.RLock()

    def __new__(cls):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        with self._singleton_lock:
            if self._initialized:
                return

            # Ensure vector DB directory exists
            VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

            # Initialize Chroma client
            self.client = chromadb.PersistentClient(
                path=str(VECTOR_DB_DIR),
                settings=chromadb.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )

            # Initialize embedding model
            model_options: dict[str, Any] = {"backend": EMBEDDING_BACKEND}
            if EMBEDDING_BACKEND == "onnx" and EMBEDDING_ONNX_FILE:
                model_options["model_kwargs"] = {"file_name": EMBEDDING_ONNX_FILE}
            logger.info(
                "Loading embedding model: %s (backend=%s)",
                EMBEDDING_MODEL,
                EMBEDDING_BACKEND,
            )
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL, **model_options)

            # Get or create collections
            self.collections = {}
            self._init_collections()

            self._initialized = True
            logger.info("VectorDB initialized successfully")

    def _init_collections(self):
        """Initialize all knowledge domain collections."""
        for name in VECTOR_DOMAINS:
            try:
                collection = self.client.get_or_create_collection(
                    name=name,
                    metadata={"hnsw:space": "cosine"}
                )
                self.collections[name] = collection
                logger.info(f"Collection '{name}' initialized (count: {collection.count()})")
            except Exception as e:
                logger.error(f"Failed to init collection {name}: {e}")

    def get_collection(self, name: str):
        """Get a collection by name."""
        if name not in self.collections:
            raise ValueError(f"Collection {name} not found")
        return self.collections[name]

    def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not text or not isinstance(text, str):
            return None
        return self.embedding_model.encode(text).tolist()

    def batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently."""
        valid_texts = [t for t in texts if t and isinstance(t, str)]
        if not valid_texts:
            return []
        return self.embedding_model.encode(valid_texts).tolist()


class VectorRetriever:
    """Handles semantic search across vector database."""

    def __init__(self):
        self.db = VectorDB()
        self.cache = OrderedDict()
        self.cache_timestamps = {}
        self._cache_lock = threading.RLock()  # Thread-safe cache access

    def _cache_key(self, query: str, collection: str, top_k: int) -> str:
        """Generate cache key."""
        return f"{collection}:{query}:{top_k}"

    def _get_cached(self, key: str) -> Optional[List[Dict]]:
        """Get cached result if not expired."""
        with self._cache_lock:
            if key not in self.cache:
                return None

            timestamp = self.cache_timestamps.get(key)
            if timestamp and datetime.now() - timestamp > timedelta(minutes=CACHE_TTL_MINUTES):
                # Cache expired, remove it
                del self.cache[key]
                del self.cache_timestamps[key]
                return None

            return self.cache[key]

    def _cache_result(self, key: str, result: List[Dict]):
        """Cache search result with LRU eviction."""
        with self._cache_lock:
            # LRU eviction: remove oldest if cache too large
            if len(self.cache) >= CACHE_MAX_SIZE:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.cache_timestamps[oldest_key]

            self.cache[key] = result
            self.cache_timestamps[key] = datetime.now()
            # Move to end (most recent)
            self.cache.move_to_end(key)

    def search_by_vector(
        self,
        query: str,
        collection_name: str,
        top_k: int = VECTOR_SEARCH_TOP_K,
        where_filter: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search collection by semantic similarity.

        Args:
            query: Search query text
            collection_name: Name of collection to search
            top_k: Number of results to return
            where_filter: Optional metadata filter (e.g., {"level": {"$eq": "1"}})

        Returns:
            List of matching documents with metadata and distance
        """
        # Validate inputs
        if not query or not isinstance(query, str):
            logger.warning(f"Invalid query: {query}")
            return []

        if not collection_name or not isinstance(collection_name, str):
            logger.warning(f"Invalid collection_name: {collection_name}")
            return []

        if not isinstance(top_k, int) or top_k < 1:
            logger.warning(f"Invalid top_k: {top_k}, using default")
            top_k = VECTOR_SEARCH_TOP_K

        # Clean query
        query = query.strip()
        if not query:
            return []

        # Check cache
        cache_key = self._cache_key(query, collection_name, top_k)
        cached = self._get_cached(cache_key)
        if cached:
            logger.debug(f"Cache hit for: {cache_key}")
            return cached

        try:
            # Get embedding for query
            query_embedding = self.db.get_embedding(query)
            if not query_embedding:
                logger.warning(f"Failed to generate embedding for query: {query}")
                return []

            collection = self.db.get_collection(collection_name)

            # Query collection
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, 10),  # Chroma limit
                where=where_filter,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = []
            if results.get("documents") and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    distance = results["distances"][0][i] if results.get("distances") else 0
                    metadata = results["metadatas"][0][i] if results.get("metadatas") else {}

                    # Convert distance (0-2 range for cosine) to similarity (0-1)
                    similarity = max(0, min(1, 1 - (distance / 2)))

                    formatted_results.append({
                        "text": doc,
                        "metadata": metadata,
                        "score": similarity,
                        "distance": distance
                    })

            # Cache result
            self._cache_result(cache_key, formatted_results)

            return formatted_results

        except ValueError as e:
            logger.warning(f"Collection not found {collection_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Vector search failed for {collection_name}: {e}", exc_info=True)
            return []

    def search_hsk_vocab(self, query: str, level: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search HSK vocabulary with optional level filtering.

        Args:
            query: Word or phrase to search
            level: HSK level to filter (e.g., "1", "2", "1-3"), or None for all

        Returns:
            List of matching HSK entries
        """
        where_filter = None
        if level and level != "不限":
            # Parse level range if needed
            if "-" in str(level):
                levels = str(level).split("-")
                where_filter = {
                    "level": {
                        "$gte": levels[0],
                        "$lte": levels[1]
                    }
                }
            else:
                where_filter = {"level": {"$eq": str(level)}}

        return self.search_by_vector(
            query,
            "hsk",
            top_k=min(10, VECTOR_SEARCH_TOP_K),
            where_filter=where_filter
        )

    def search_semantic(
        self,
        query: str,
        domain: str,
        top_k: int = VECTOR_SEARCH_TOP_K
    ) -> List[Dict[str, Any]]:
        """
        Semantic search in a specific domain.

        Args:
            query: Search query
            domain: Knowledge domain, including the traceable Haipai culture corpus.
            top_k: Number of results

        Returns:
            List of relevant documents
        """
        if domain not in VECTOR_DOMAINS:
            logger.warning(f"Unknown domain: {domain}")
            return []

        return self.search_by_vector(query, domain, top_k=top_k)

    def format_for_context(
        self,
        results: List[Dict[str, Any]],
        max_chars: int = MAX_CONTEXT_CHARS,
        domain: str = "general"
    ) -> str:
        """
        Format search results as context for LLM.

        Args:
            results: Search results from vector search
            max_chars: Maximum context length
            domain: Domain name for formatting context

        Returns:
            Formatted context string
        """
        if not results:
            return ""

        context_lines = []
        current_length = 0

        # Format based on domain
        if domain == "hsk":
            context_lines.append("HSK知识库相关词汇及信息：\n")
            for result in results:
                text = result.get("text", "")
                metadata = result.get("metadata", {})
                score = result.get("score", 0)

                line = f"- {text}"
                if metadata.get("level"):
                    line += f" [HSK{metadata['level']}级]"
                if metadata.get("pinyin"):
                    line += f" ({metadata['pinyin']})"
                line += f" (相关度: {score:.2%})\n"

                if current_length + len(line) <= max_chars:
                    context_lines.append(line)
                    current_length += len(line)
                else:
                    break

        elif domain == "mucgec":
            context_lines.append("汉语纠错相关规范与示例：\n")
            for result in results:
                text = result.get("text", "")
                score = result.get("score", 0)
                line = f"- {text[:200]}... (相关度: {score:.2%})\n"

                if current_length + len(line) <= max_chars:
                    context_lines.append(line)
                    current_length += len(line)
                else:
                    break

        else:
            # Generic formatting for other domains
            for result in results:
                text = result.get("text", "")
                metadata = result.get("metadata", {})
                score = result.get("score", 0)

                # Truncate long texts
                if len(text) > 300:
                    text = text[:300] + "..."

                line = f"- {text} (相关度: {score:.2%})\n"

                if current_length + len(line) <= max_chars:
                    context_lines.append(line)
                    current_length += len(line)
                else:
                    break

        return "".join(context_lines)

    def clear_cache(self):
        """Clear the search cache."""
        with self._cache_lock:
            self.cache.clear()
            self.cache_timestamps.clear()
        logger.info("Search cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        with self._cache_lock:
            return {
                "cached_queries": len(self.cache),
                "max_cache_size": CACHE_MAX_SIZE,
                "ttl_minutes": CACHE_TTL_MINUTES
            }


# Global retriever instance
_vector_retriever = None


def get_vector_retriever() -> VectorRetriever:
    """Get or create global vector retriever instance."""
    global _vector_retriever
    if _vector_retriever is None:
        _vector_retriever = VectorRetriever()
    return _vector_retriever
