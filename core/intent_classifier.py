from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .llm_client import DEEPSEEK_MODEL, client

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IntentCandidate:
    key: str
    name: str
    description: str
    examples: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()


@dataclass(frozen=True)
class IntentResult:
    intent: str
    confidence: str
    source: str
    evidence: str
    domains: tuple[str, ...]
    score: float = 0.0


def _extract_json_object(raw_text: str) -> dict[str, str]:
    text = str(raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("模型未返回有效 JSON 对象")
    return json.loads(text[start : end + 1])


def _tfidf_rank(query: str, candidates: Sequence[IntentCandidate]) -> tuple[int, float, float]:
    docs = []
    for candidate in candidates:
        examples = " ".join(candidate.examples)
        docs.append(f"{candidate.name} {candidate.description} {examples}".strip())

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(1, 3),
        max_features=8000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(docs)
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, matrix).flatten()

    top_idx = int(scores.argmax())
    top_score = float(scores[top_idx])
    second_score = float(sorted(scores, reverse=True)[1]) if len(scores) > 1 else 0.0
    return top_idx, top_score, second_score


def _classify_with_llm(query: str, candidates: Sequence[IntentCandidate]) -> tuple[str, str, str]:
    options = [
        {
            "key": c.key,
            "name": c.name,
            "description": c.description,
            "examples": list(c.examples),
        }
        for c in candidates
    ]
    system_prompt = """
你是中文教学系统的意图识别器。请从候选意图中选择最匹配的一个。

请只返回一个 JSON 对象：
{
  "intent": "候选意图 key",
  "confidence": "high | medium | low",
  "reason": "不超过40字说明"
}

规则：
- 只能从候选意图中选择。
- 若信息不足，选择最通用的候选意图。
""".strip()

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": query,
                        "candidates": options,
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        temperature=0.1,
    )
    payload = _extract_json_object(response.choices[0].message.content or "{}")
    intent = str(payload.get("intent", "")).strip()
    confidence = str(payload.get("confidence", "low")).strip().lower() or "low"
    reason = str(payload.get("reason", "")).strip()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
    return intent, confidence, reason


def classify_intent(
    query: str,
    candidates: Sequence[IntentCandidate],
    min_score: float = 0.16,
    margin: float = 0.04,
) -> IntentResult:
    if not candidates:
        raise ValueError("candidates 不能为空")

    query = str(query or "").strip()
    if not query:
        fallback = candidates[0]
        return IntentResult(
            intent=fallback.key,
            confidence="low",
            source="fallback",
            evidence="用户输入为空，回退默认意图",
            domains=fallback.domains,
            score=0.0,
        )

    top_idx, top_score, second_score = _tfidf_rank(query, candidates)
    best = candidates[top_idx]
    if top_score >= min_score and (top_score - second_score) >= margin:
        return IntentResult(
            intent=best.key,
            confidence="medium",
            source="semantic",
            evidence=f"TF-IDF 相似度命中: {best.name}",
            domains=best.domains,
            score=top_score,
        )

    try:
        intent_key, confidence, reason = _classify_with_llm(query, candidates)
        selected = next((c for c in candidates if c.key == intent_key), best)
        return IntentResult(
            intent=selected.key,
            confidence=confidence,
            source="llm",
            evidence=reason or "LLM 意图判别",
            domains=selected.domains,
            score=top_score,
        )
    except Exception as exc:
        logger.warning("LLM 意图识别失败: %s", exc)
        return IntentResult(
            intent=best.key,
            confidence="low",
            source="semantic_fallback",
            evidence="LLM 识别失败，回退语义相似度",
            domains=best.domains,
            score=top_score,
        )
