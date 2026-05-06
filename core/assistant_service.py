from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .account_profiles import TeacherProfile
from .ai_agent import generate_response
from .skills.runtime import execute_skill, render_skill_result


@dataclass(frozen=True)
class AssistantSkill:
    key: str
    label: str
    description: str
    mode: str = "skill"


ASSISTANT_SKILLS = (
    AssistantSkill(
        key="teacher_advisor",
        label="教学顾问",
        description="面向国际中文教学场景的综合问答、建议和知识库辅助回答。",
        mode="advisor",
    ),
    AssistantSkill(
        key="bridge_translate",
        label="跨语种翻译",
        description="把教学文本翻译成目标语言，并补充可选拼音与词汇说明。",
    ),
    AssistantSkill(
        key="bridge_correct",
        label="中文批改",
        description="对学习者文本进行纠错、分析偏误并给出教学建议。",
    ),
    AssistantSkill(
        key="bridge_lesson_design",
        label="教学设计咨询",
        description="生成课堂目标、流程、活动和评价建议。",
    ),
    AssistantSkill(
        key="bridge_hsk_coaching",
        label="HSK 备考指导",
        description="制定 HSK 备考计划、重点能力和模拟策略。",
    ),
    AssistantSkill(
        key="bridge_tool_recommendation",
        label="数字化工具推荐",
        description="根据教学场景推荐合适的工具和落地步骤。",
    ),
    AssistantSkill(
        key="bridge_policy_interpretation",
        label="政策法规解读",
        description="解释国际中文教育相关政策、标准和合规行动。",
    ),
)

_SKILL_INDEX = {item.key: item for item in ASSISTANT_SKILLS}


def list_assistant_skills() -> list[dict[str, str]]:
    return [
        {
            "key": skill.key,
            "label": skill.label,
            "description": skill.description,
            "mode": skill.mode,
        }
        for skill in ASSISTANT_SKILLS
    ]


def _history_to_tuples(history: list[dict[str, Any]] | None) -> list[tuple[str, str]]:
    if not history:
        return []

    tuples: list[tuple[str, str]] = []
    current_user = ""
    for item in history:
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role == "user":
            current_user = content
        elif role == "assistant":
            tuples.append((current_user, content))
            current_user = ""
    return tuples


def run_assistant_turn(
    *,
    skill_key: str,
    text: str,
    profile: TeacherProfile,
    history: list[dict[str, Any]] | None = None,
) -> str:
    resolved_skill_key = str(skill_key or "teacher_advisor").strip() or "teacher_advisor"
    user_text = str(text or "").strip()

    if not user_text:
        return "请输入你的问题或文本。"

    skill = _SKILL_INDEX.get(resolved_skill_key)
    if skill is None:
        raise ValueError(f"未知 skill: {resolved_skill_key}")

    if skill.mode == "advisor":
        return generate_response(
            user_text,
            history=_history_to_tuples(history),
            hsk_level="自动判断",
            account_id=profile.account_id,
        )

    payload = execute_skill(
        resolved_skill_key,
        user_text,
        instruction_language=profile.instruction_language,
        instruction_languages=profile.teaching_languages_display,
        teacher_level=profile.teacher_level,
        target_level="General",
    )
    return render_skill_result(payload)
