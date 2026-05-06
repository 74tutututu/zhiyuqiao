from __future__ import annotations

from dataclasses import dataclass

from .intent_classifier import IntentCandidate, IntentResult, classify_intent
from .retriever import get_relevant_info_by_domains


@dataclass(frozen=True)
class SkillRoutingResult:
    intent: str
    domains: tuple[str, ...]
    source: str
    evidence: str


SKILL_INTENT_CANDIDATES = (
    IntentCandidate(
        key="lesson_design",
        name="教学设计咨询",
        description="课堂目标设定、教学流程、课堂活动设计和评价建议",
        examples=(
            "如何设计零基础第一堂中文课",
            "请给我一份45分钟教学流程",
            "课堂活动怎么安排",
        ),
        domains=("strategies", "references", "teacher"),
    ),
    IntentCandidate(
        key="hsk_prep",
        name="HSK 备考指导",
        description="HSK 考试备考、等级要求、词汇语法重点和备考策略",
        examples=(
            "HSK4 阅读理解备考",
            "HSK3 词汇怎么规划",
            "口语考试技巧",
        ),
        domains=("hsk", "strategies"),
    ),
    IntentCandidate(
        key="tools",
        name="数字化工具推荐",
        description="教学平台、课堂互动工具、在线课堂技术与选型建议",
        examples=(
            "有什么适合中文教学的免费工具",
            "在线课堂工具推荐",
            "教学平台怎么选",
        ),
        domains=("softwares",),
    ),
    IntentCandidate(
        key="policy",
        name="政策法规解读",
        description="国际中文教育政策、教师标准、法规与合规要求解读",
        examples=(
            "国际中文教育政策变化",
            "教师能力标准解读",
            "政策对课程设计影响",
        ),
        domains=("teacher", "references"),
    ),
    IntentCandidate(
        key="correction",
        name="中文纠错",
        description="中文写作与语法纠错、偏误分析与教学建议",
        examples=("帮我改错", "这句有没有问题", "作文批改"),
        domains=("mucgec",),
    ),
    IntentCandidate(
        key="translation",
        name="教学翻译",
        description="教学场景翻译、讲解用翻译和词汇提示",
        examples=("翻译并解释", "帮我翻成中文", "课堂指令翻译"),
        domains=("references", "strategies"),
    ),
    IntentCandidate(
        key="general",
        name="通用教学咨询",
        description="泛教学咨询或未明确分类的问题",
        examples=("教学建议", "怎么教好中文", "课堂管理"),
        domains=("teacher", "references"),
    ),
)

SKILL_FIXED_INTENTS = {
    "bridge_lesson_design": "lesson_design",
    "bridge_hsk_coaching": "hsk_prep",
    "bridge_tool_recommendation": "tools",
    "bridge_policy_interpretation": "policy",
    "bridge_correct": "correction",
    "bridge_translate": "translation",
}


def resolve_skill_intent(skill_key: str, query: str) -> SkillRoutingResult:
    fixed = SKILL_FIXED_INTENTS.get(skill_key)
    if fixed:
        candidate = next(c for c in SKILL_INTENT_CANDIDATES if c.key == fixed)
        return SkillRoutingResult(
            intent=candidate.key,
            domains=candidate.domains,
            source="fixed",
            evidence=f"技能固定意图: {candidate.name}",
        )

    result: IntentResult = classify_intent(query, SKILL_INTENT_CANDIDATES)
    return SkillRoutingResult(
        intent=result.intent,
        domains=result.domains,
        source=result.source,
        evidence=result.evidence,
    )


def build_skill_knowledge_context(
    skill_key: str,
    query: str,
    hsk_level: str = "不限",
) -> tuple[str, SkillRoutingResult]:
    routing = resolve_skill_intent(skill_key, query)
    context = get_relevant_info_by_domains(query, routing.domains, hsk_level=hsk_level)
    return context, routing
