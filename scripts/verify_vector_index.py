"""Verify that the production vector index is complete and useful."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.vector_retriever import VECTOR_DOMAINS, get_vector_retriever  # noqa: E402


def main() -> int:
    retriever = get_vector_retriever()
    counts = {
        domain: retriever.db.get_collection(domain).count()
        for domain in VECTOR_DOMAINS
    }
    empty = [domain for domain, count in counts.items() if count <= 0]
    if empty:
        raise RuntimeError(f"Empty vector collections: {', '.join(empty)}")

    query = "杨浦滨江工业遗产如何变成HSK三级中文观察任务"
    results = retriever.search_semantic(query, "haipai", top_k=3)
    relevant = any(
        "杨浦滨江" in str(item.get("text", ""))
        or "工业遗产" in str(item.get("text", ""))
        for item in results
    )
    if not relevant:
        raise RuntimeError("Haipai semantic smoke query did not retrieve Yangpu heritage evidence.")

    print(json.dumps({
        "status": "ok",
        "collections": counts,
        "total": sum(counts.values()),
        "haipai_smoke_scores": [round(float(item.get("score", 0)), 4) for item in results],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
