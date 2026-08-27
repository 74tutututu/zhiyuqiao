from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .account_profiles import AccountProfile
from .ai_agent import generate_response
from .skills.runtime import execute_skill, render_skill_result


@dataclass(frozen=True)
class AssistantSkill:
    key: str
    label: str
    description: str
    icon: str
    roles: tuple[str, ...]
    mode: str = "skill"
    runtime_key: str = ""
    prompt_prefix: str = ""
    starter_prompts: tuple[str, ...] = ()


ASSISTANT_SKILLS = (
    AssistantSkill(
        key="haipai_lesson_lab",
        label="海派文化课程实验室",
        description="把上海文化场景转化为分级、可执行、可核验的中文课堂任务。",
        icon="海",
        roles=("teacher",),
        mode="advisor",
        prompt_prefix=(
            "你正在使用智语桥的海派文化课程实验室。请优先围绕海派文化与上海真实城市场景，"
            "明确学习者中文水平、语言支架、文化事实来源、交际任务、形成性评价和教师核验点。"
        ),
        starter_prompts=(
            "为HSK1学习者设计10分钟外滩与陆家嘴对比活动",
            "把杨浦滨江工业遗产改造成HSK3口语任务",
            "设计一节茶与咖啡主题的跨文化中文课",
        ),
    ),
    AssistantSkill(
        key="teacher_advisor",
        label="教学顾问",
        description="围绕学情、课堂组织、资源选择与教学难点给出综合建议。",
        icon="教",
        roles=("teacher",),
        mode="advisor",
        starter_prompts=(
            "如何帮助初级学习者理解上海城市文化？",
            "为一节混合水平中文课设计差异化任务",
        ),
    ),
    AssistantSkill(
        key="bridge_lesson_design",
        label="教学设计",
        description="生成目标、流程、活动、材料与评价一致的课堂方案。",
        icon="案",
        roles=("teacher",),
        runtime_key="bridge_lesson_design",
        starter_prompts=(
            "设计一节45分钟的上海地铁公共文明主题课",
            "把建筑可阅读任务改成小组项目",
        ),
    ),
    AssistantSkill(
        key="bridge_translate",
        label="跨语种解释",
        description="翻译教学或学习文本，并补充拼音、词汇和语境提示。",
        icon="译",
        roles=("teacher", "student"),
        runtime_key="bridge_translate",
        starter_prompts=(
            "用英语解释‘海纳百川’，并给出两个中文例句",
            "把这段上海城市介绍改写成适合初学者的双语文本",
        ),
    ),
    AssistantSkill(
        key="bridge_correct",
        label="中文表达反馈",
        description="批改中文句子或短文，解释偏误并给出自然表达。",
        icon="改",
        roles=("teacher", "student"),
        runtime_key="bridge_correct",
        starter_prompts=(
            "请帮我修改：上海的建筑让我感觉历史和现代一起。",
            "批改这段中文，并告诉我最需要练习的三个问题",
        ),
    ),
    AssistantSkill(
        key="bridge_hsk_coaching",
        label="HSK 学习计划",
        description="制定阶段计划、能力重点、资源安排和模拟练习策略。",
        icon="考",
        roles=("teacher", "student"),
        runtime_key="bridge_hsk_coaching",
        starter_prompts=(
            "为我制定四周HSK3复习计划",
            "我听力较弱，如何安排每天30分钟练习？",
        ),
    ),
    AssistantSkill(
        key="bridge_tool_recommendation",
        label="数字教学工具",
        description="按课堂或作业场景推荐工具，并给出可落地的使用步骤。",
        icon="具",
        roles=("teacher",),
        runtime_key="bridge_tool_recommendation",
        starter_prompts=(
            "推荐适合国际学生城市观察任务的协作工具",
            "如何低成本收集课堂即时反馈？",
        ),
    ),
    AssistantSkill(
        key="bridge_policy_interpretation",
        label="标准与政策",
        description="解释国际中文教育标准、数字教育政策和教学合规边界。",
        icon="规",
        roles=("teacher",),
        runtime_key="bridge_policy_interpretation",
        starter_prompts=(
            "三等九级标准如何用于海派文化任务分级？",
            "AI生成教学材料需要注意哪些审核边界？",
        ),
    ),
    AssistantSkill(
        key="culture_explorer",
        label="海派文化探索",
        description="用适合你中文水平的方式认识上海，并完成真实交际任务。",
        icon="沪",
        roles=("student",),
        mode="advisor",
        prompt_prefix=(
            "你是智语桥的海派文化学习伙伴。请根据学习者中文水平，用清晰、友好、不过度困难的中文回答；"
            "围绕上海真实文化场景解释关键词与背景，区分可核验事实和文化解释，并设计一个能在现实中完成的小任务。"
            "涉及票价、开放时间、交通班次等动态信息时，不要凭记忆给出确定数字，应提示学习者以场馆或运营方最新公告为准。"
        ),
        starter_prompts=(
            "我想用中文看懂外滩建筑，从哪里开始？",
            "为什么上海人会说‘侬好’？我应该怎么用？",
            "带我完成一次杨浦滨江中文观察任务",
        ),
    ),
    AssistantSkill(
        key="student_tutor",
        label="中文学习伙伴",
        description="解释词汇、语法和生活表达，按你的水平给例句与练习。",
        icon="学",
        roles=("student",),
        mode="advisor",
        prompt_prefix=(
            "你是国际中文学习伙伴。请按学习者当前水平解释，先给直接答案，再给简短例句和一个小练习；"
            "不要使用明显超出学习者水平且未解释的词语。"
        ),
        starter_prompts=(
            "‘一边……一边……’怎么用？",
            "在上海问路时，我可以怎么说？",
        ),
    ),
    AssistantSkill(
        key="speaking_partner",
        label="情景口语陪练",
        description="围绕城市生活进行角色对话，提供提示、追问和即时反馈。",
        icon="说",
        roles=("student",),
        mode="advisor",
        prompt_prefix=(
            "你是中文情景口语陪练。请先说明场景和双方角色，每轮只提出一个适合学习者水平的问题，"
            "根据回答给简短纠正和更自然说法，再继续对话。"
        ),
        starter_prompts=(
            "和我练习在咖啡店点单，你做店员",
            "模拟我向同学介绍外滩和陆家嘴",
        ),
    ),
)

_SKILL_INDEX = {item.key: item for item in ASSISTANT_SKILLS}


def list_assistant_skills(account_role: str = "teacher") -> list[dict[str, Any]]:
    resolved_role = "student" if account_role == "student" else "teacher"
    preferred_order = {
        "teacher": [
            "haipai_lesson_lab", "teacher_advisor", "bridge_lesson_design", "bridge_translate",
            "bridge_correct", "bridge_hsk_coaching", "bridge_tool_recommendation", "bridge_policy_interpretation",
        ],
        "student": [
            "culture_explorer", "student_tutor", "speaking_partner",
            "bridge_translate", "bridge_correct", "bridge_hsk_coaching",
        ],
    }
    order_index = {key: index for index, key in enumerate(preferred_order[resolved_role])}
    role_skills = sorted(
        (skill for skill in ASSISTANT_SKILLS if resolved_role in skill.roles),
        key=lambda skill: order_index.get(skill.key, len(order_index)),
    )
    return [
        {
            "key": skill.key,
            "label": skill.label,
            "description": skill.description,
            "icon": skill.icon,
            "mode": skill.mode,
            "starter_prompts": list(skill.starter_prompts),
        }
        for skill in role_skills
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


def _target_level(profile: AccountProfile) -> str:
    if not profile.is_student:
        return "General"
    if profile.student_level in {"starter", "hsk1"}:
        return "HSK1"
    if profile.student_level == "hsk2":
        return "HSK2"
    if profile.student_level == "hsk3":
        return "HSK3"
    if profile.student_level == "hsk4":
        return "HSK4"
    if profile.student_level in {"hsk5", "hsk6", "advanced"}:
        return "Advanced"
    return "General"


def run_assistant_turn(
    *,
    skill_key: str,
    text: str,
    profile: AccountProfile,
    history: list[dict[str, Any]] | None = None,
) -> str:
    resolved_skill_key = str(skill_key or "").strip()
    user_text = str(text or "").strip()

    if not user_text:
        return "请输入你的问题或文本。"

    allowed = list_assistant_skills(profile.account_role)
    default_key = allowed[0]["key"] if allowed else "teacher_advisor"
    resolved_skill_key = resolved_skill_key or default_key
    skill = _SKILL_INDEX.get(resolved_skill_key)
    if skill is None or profile.account_role not in skill.roles:
        raise ValueError("当前账号不能使用该功能，请刷新页面后重试。")

    role_context = (
        f"学习者当前水平：{profile.student_level_label}；学习目标：{profile.learning_goal_label}。"
        if profile.is_student
        else f"教师画像：{profile.teacher_role_label}；教学语种：{profile.teaching_languages_display}。"
    )
    enriched_text = "\n\n".join(part for part in (skill.prompt_prefix, role_context, user_text) if part)

    if skill.mode == "advisor":
        return generate_response(
            enriched_text,
            history=_history_to_tuples(history),
            hsk_level=profile.student_level_label if profile.is_student else "自动判断",
            account_id=profile.account_id,
        )

    runtime_key = skill.runtime_key or resolved_skill_key
    payload = execute_skill(
        runtime_key,
        enriched_text,
        instruction_language=profile.instruction_language,
        instruction_languages=profile.teaching_languages_display,
        teacher_level=profile.teacher_level if profile.is_teacher else "learner",
        target_level=_target_level(profile),
    )
    return render_skill_result(payload)
