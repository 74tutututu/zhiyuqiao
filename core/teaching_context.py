from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .llm_client import DEEPSEEK_MODEL, client

AUTO_LEARNER_LEVEL = "自动判断"
GENERAL_LEARNER_LEVEL = "通用"
DEFAULT_RETRIEVAL_LEVEL = "不限"

EXPLICIT_GENERAL_HINTS = {
    "",
    AUTO_LEARNER_LEVEL,
    GENERAL_LEARNER_LEVEL,
    DEFAULT_RETRIEVAL_LEVEL,
}

LLM_LEVEL_LABELS = {
    "zero_beginner": "零基础",
    "beginner": "初级",
    "intermediate": "中级",
    "advanced": "高级",
    "general": GENERAL_LEARNER_LEVEL,
}

HSK_LEVEL_RE = re.compile(r"HSK\s*([1-6])", re.IGNORECASE)

LEVEL_PATTERNS = (
    (("零基础", "零起点", "启蒙", "拼音入门", "第一堂中文课"), "零基础"),
    (("初级", "入门", "初学者", "基础班", "简单句"), "初级"),
    (("中级", "进阶", "HSK3", "HSK4"), "中级"),
    (("高级", "高阶", "学术写作", "HSK5", "HSK6"), "高级"),
)

TEACHING_GOAL_PATTERNS = (
    (("教案", "教学设计", "课堂活动", "第一堂课", "怎么上课"), "lesson_design"),
    (("词汇", "词语", "生词"), "vocabulary"),
    (("语法", "句型", "偏误"), "grammar"),
    (("口语", "会话", "表达"), "speaking"),
    (("阅读", "阅读理解"), "reading"),
    (("写作", "作文"), "writing"),
    (("听力",), "listening"),
    (("备考", "考试", "真题"), "exam_prep"),
    (("工具", "软件", "平台"), "tools"),
    (("政策", "标准", "教师发展"), "policy"),
)


@dataclass(frozen=True)
class TeachingContext:
    learner_level: str = GENERAL_LEARNER_LEVEL
    confidence: str = "low"
    teaching_goal: str = "general"
    evidence: str = ""
    source: str = "fallback"
    retrieval_hsk_level: str = DEFAULT_RETRIEVAL_LEVEL


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


def _normalize_history_text(history: list[tuple[str, str]] | None) -> str:
    if not history:
        return ""
    snippets: list[str] = []
    for user_msg, _ in history[-3:]:
        clean = str(user_msg or "").strip()
        if clean:
            snippets.append(clean)
    return "\n".join(snippets[-3:])


def _extract_explicit_hsk_level(text: str) -> str | None:
    match = HSK_LEVEL_RE.search(text)
    if not match:
        return None
    return f"HSK {match.group(1)}"


def _infer_goal_from_keywords(text: str) -> str:
    lowered = text.lower()
    for keywords, goal in TEACHING_GOAL_PATTERNS:
        if any(keyword.lower() in lowered for keyword in keywords):
            return goal
    return "general"


def _infer_from_heuristics(text: str) -> TeachingContext | None:
    explicit_hsk = _extract_explicit_hsk_level(text)
    if explicit_hsk:
        return TeachingContext(
            learner_level=explicit_hsk,
            confidence="high",
            teaching_goal=_infer_goal_from_keywords(text),
            evidence=f"检测到明确等级表述：{explicit_hsk}",
            source="heuristic",
            retrieval_hsk_level=explicit_hsk,
        )

    lowered = text.lower()
    for keywords, learner_level in LEVEL_PATTERNS:
        for keyword in keywords:
            if keyword.lower() in lowered:
                return TeachingContext(
                    learner_level=learner_level,
                    confidence="medium",
                    teaching_goal=_infer_goal_from_keywords(text),
                    evidence=f"检测到教学对象线索：{keyword}",
                    source="heuristic",
                    retrieval_hsk_level=DEFAULT_RETRIEVAL_LEVEL,
                )
    return None


def _infer_with_llm(current_question: str, history_text: str) -> TeachingContext | None:
    system_prompt = """
你是国际中文教育助理的上下文分析器。你的任务不是回答问题，而是判断当前问题对应的学生水平与教学目标。

请只返回一个 JSON 对象，字段如下：
{
  "learner_level": "zero_beginner | beginner | intermediate | advanced | general",
  "confidence": "high | medium | low",
  "teaching_goal": "lesson_design | vocabulary | grammar | speaking | reading | writing | listening | exam_prep | tools | policy | general",
  "reason": "不超过40字的中文说明"
}

规则：
- 只有在教师提问中存在明显线索时，才判断具体学生水平。
- 如果没有明显线索，必须返回 general。
- 不要臆测具体 HSK 数字，除非输入里明确出现 HSK 级别。
""".strip()

    user_payload = {
        "recent_teacher_questions": history_text,
        "current_question": current_question,
    }

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        temperature=0.1,
    )

    payload = _extract_json_object(response.choices[0].message.content or "{}")
    learner_level_key = str(payload.get("learner_level", "general")).strip().lower()
    confidence = str(payload.get("confidence", "low")).strip().lower() or "low"
    teaching_goal = str(payload.get("teaching_goal", "general")).strip().lower() or "general"
    reason = str(payload.get("reason", "")).strip()

    return TeachingContext(
        learner_level=LLM_LEVEL_LABELS.get(learner_level_key, GENERAL_LEARNER_LEVEL),
        confidence=confidence if confidence in {"high", "medium", "low"} else "low",
        teaching_goal=teaching_goal,
        evidence=reason,
        source="llm",
        retrieval_hsk_level=DEFAULT_RETRIEVAL_LEVEL,
    )


def analyze_teaching_context(
    current_question: str,
    history: list[tuple[str, str]] | None = None,
    learner_level_hint: str | None = None,
) -> TeachingContext:
    normalized_hint = str(learner_level_hint or "").strip()
    if normalized_hint and normalized_hint not in EXPLICIT_GENERAL_HINTS:
        retrieval_level = normalized_hint if normalized_hint.startswith("HSK") else DEFAULT_RETRIEVAL_LEVEL
        return TeachingContext(
            learner_level=normalized_hint,
            confidence="high",
            teaching_goal=_infer_goal_from_keywords(current_question),
            evidence="使用了用户手动指定的学生水平提示。",
            source="manual",
            retrieval_hsk_level=retrieval_level,
        )

    if normalized_hint == GENERAL_LEARNER_LEVEL:
        return TeachingContext(
            learner_level=GENERAL_LEARNER_LEVEL,
            confidence="high",
            teaching_goal=_infer_goal_from_keywords(current_question),
            evidence="用户要求按通用水准回答。",
            source="manual",
            retrieval_hsk_level=DEFAULT_RETRIEVAL_LEVEL,
        )

    history_text = _normalize_history_text(history)
    combined_text = "\n".join(part for part in [history_text, current_question] if part).strip()

    explicit_hsk = _extract_explicit_hsk_level(combined_text)
    if explicit_hsk:
        return TeachingContext(
            learner_level=explicit_hsk,
            confidence="high",
            teaching_goal=_infer_goal_from_keywords(combined_text),
            evidence=f"检测到明确等级表述：{explicit_hsk}",
            source="explicit",
            retrieval_hsk_level=explicit_hsk,
        )

    try:
        llm_result = _infer_with_llm(current_question, history_text)
        if llm_result is not None:
            return llm_result
    except Exception:
        pass

    heuristic_result = _infer_from_heuristics(combined_text)
    if heuristic_result is not None:
        return heuristic_result

    return TeachingContext(
        learner_level=GENERAL_LEARNER_LEVEL,
        confidence="low",
        teaching_goal=_infer_goal_from_keywords(current_question),
        evidence="未检测到稳定的学生水平线索，回退为通用水准。",
        source="fallback",
        retrieval_hsk_level=DEFAULT_RETRIEVAL_LEVEL,
    )
