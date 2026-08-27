"""
Health check and monitoring utilities for ZhiYuQiao system.

Provides diagnostic functions to verify system status, dependency availability,
and vector database integrity.
"""

import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


def check_vector_db_status() -> Dict[str, Any]:
    """Check if vector database is operational."""
    try:
        from .vector_retriever import VectorDB, get_vector_retriever

        db = VectorDB()
        retriever = get_vector_retriever()

        collections = list(db.collections.keys())
        cache_stats = retriever.get_cache_stats()

        return {
            "status": "OK",
            "db_type": "Chroma",
            "collections": collections,
            "collection_count": len(collections),
            "cache_stats": cache_stats,
            "timestamp": datetime.now().isoformat()
        }
    except ImportError as e:
        return {
            "status": "NOT_AVAILABLE",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Vector DB health check failed: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def check_retriever_status() -> Dict[str, Any]:
    """Check if knowledge base retriever is operational."""
    try:
        from .retriever import get_relevant_info, KnowledgeBase, _kb

        # Test retriever initialization
        _kb.initialize()

        # Test a simple query
        test_result = get_relevant_info("测试查询", "不限")

        return {
            "status": "OK",
            "retriever_initialized": True,
            "tfidf_domains": list(_kb.tfidf_indices.keys()) if hasattr(_kb, 'tfidf_indices') else [],
            "result_sample_length": len(test_result),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Retriever health check failed: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def check_ai_agent_status() -> Dict[str, Any]:
    """Check if AI agent dependencies are available."""
    try:
        import os
        from .ai_agent import client, REVIEW_NOTICE

        api_key_present = bool(os.getenv("DEEPSEEK_API_KEY"))

        return {
            "status": "OK",
            "api_key_configured": api_key_present,
            "client_initialized": client is not None,
            "review_notice_present": bool(REVIEW_NOTICE),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"AI agent health check failed: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def full_system_health_check() -> Dict[str, Any]:
    """
    Perform a comprehensive health check of the entire system.

    Returns:
        Dictionary with status of all components
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "vector_db": check_vector_db_status(),
        "retriever": check_retriever_status(),
        "ai_agent": check_ai_agent_status(),
    }


def get_system_summary() -> str:
    """
    Get a human-readable system health summary.

    Returns:
        String with system status summary
    """
    health = full_system_health_check()

    lines = [
        "=== ZhiYuQiao System Health Check ===",
        f"Timestamp: {health['timestamp']}\n",
    ]

    # Vector DB status
    vdb = health["vector_db"]
    lines.append(f"Vector DB: {vdb['status']}")
    if vdb["status"] == "OK":
        lines.append(f"  Collections: {', '.join(vdb['collections'])}")
        lines.append(f"  Cached queries: {vdb['cache_stats']['cached_queries']}")
    else:
        lines.append(f"  Error: {vdb.get('error', 'Unknown')}")

    # Retriever status
    ret = health["retriever"]
    lines.append(f"\nRetriever: {ret['status']}")
    if ret["status"] == "OK":
        lines.append(f"  TF-IDF domains: {', '.join(ret['tfidf_domains'])}")
    else:
        lines.append(f"  Error: {ret.get('error', 'Unknown')}")

    # AI Agent status
    ai = health["ai_agent"]
    lines.append(f"\nAI Agent: {ai['status']}")
    if ai["status"] == "OK":
        api_status = "Configured" if ai["api_key_configured"] else "NOT CONFIGURED"
        lines.append(f"  API Key: {api_status}")
    else:
        lines.append(f"  Error: {ai.get('error', 'Unknown')}")

    return "\n".join(lines)


if __name__ == "__main__":
    print(get_system_summary())
