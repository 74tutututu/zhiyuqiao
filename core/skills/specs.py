from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SkillInputSpec:
    name: str
    type: str
    description: str
    choices: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillSpec:
    key: str
    name: str
    description: str
    inputs: tuple[SkillInputSpec, ...]
    implementation_logic: tuple[str, ...]
    evaluation_criteria: tuple[str, ...]
    output_fields: tuple[str, ...]
    refusal_message: str
    default_params: dict[str, Any] = field(default_factory=dict)
    ui_label: str = ""


BRIDGE_TRANSLATE_SPEC = SkillSpec(
    key="bridge_translate",
    name="跨语种翻译",
    description="将用户输入翻译为教学场景所需的目标语言，并在输出含中文时补充拼音与核心词汇提示。",
    inputs=(
        SkillInputSpec("source_text", "string", "待翻译的原文或教学文本"),
        SkillInputSpec(
            "instruction_language",
            "string",
            "首选讲解语言，通常跟账号的主教学语言一致",
        ),
        SkillInputSpec(
            "instruction_languages",
            "string",
            "当前账号可使用的全部教学语言列表，用于帮助模型决定解释语言",
        ),
        SkillInputSpec(
            "teacher_level",
            "string",
            "当前账号的教师水平，用于控制解释深浅",
        ),
        SkillInputSpec(
            "target_language",
            "string",
            "目标翻译语言；auto 表示优先根据用户指令判断，否则回退到账号主教学语言",
        ),
        SkillInputSpec(
            "target_level",
            "enum",
            "教学说明层级；默认使用 General，翻译本身不强制贴合某个固定 HSK 等级",
            ("General", "HSK1", "HSK2", "Advanced"),
        ),
    ),
    implementation_logic=(
        "识别用户是否明确指定了目标语言；如果明确指定，必须优先翻译到该语言。",
        "如果用户没有指定目标语言，则默认使用账号主教学语言作为译文语言。",
        "仅在输出包含中文时补充拼音；如果译文不是中文，不要强行生成拼音。",
        "提取最多 3 个核心词汇，给出简短、教学友好的解释。",
        "返回结构化 JSON，便于界面和 API 复用。",
    ),
    evaluation_criteria=(
        "输出必须包含 translation 与 pinyin 字段。",
        "vocabulary_notes 不得超过 3 项。",
        "敏感内容必须返回预设拒绝话术。",
    ),
    output_fields=("intent", "translation", "pinyin", "vocabulary_notes", "teaching_note"),
    refusal_message="抱歉，这条内容不适合用于国际中文教学辅助场景，我不能继续处理。",
    default_params={
        "target_level": "General",
        "instruction_language": "中文",
        "instruction_languages": "中文",
        "teacher_level": "experienced_teacher",
        "target_language": "auto",
    },
    ui_label="跨语种翻译",
)


BRIDGE_CORRECT_SPEC = SkillSpec(
    key="bridge_correct",
    name="中文批改",
    description="针对中文学习者的作文、句子或练习答案进行批改，并给出教学友好的纠错说明。",
    inputs=(
        SkillInputSpec("source_text", "string", "待批改的中文文本"),
        SkillInputSpec(
            "instruction_language",
            "string",
            "首选讲解语言，通常跟账号的主教学语言一致",
        ),
        SkillInputSpec(
            "instruction_languages",
            "string",
            "当前账号可使用的全部教学语言列表，用于帮助模型决定解释语言",
        ),
        SkillInputSpec(
            "teacher_level",
            "string",
            "当前账号的教师水平，用于控制解释深浅",
        ),
        SkillInputSpec(
            "target_level",
            "enum",
            "教学说明层级；General 表示通用表达，不强行贴合某个固定 HSK 等级",
            ("General", "HSK1", "HSK2", "Advanced"),
        ),
    ),
    implementation_logic=(
        "先识别用户是要逐句批改，还是想问某个语法点。",
        "给出更自然或更准确的改写结果。",
        "提炼最多 3 个关键错误点，并使用适合 target_level 的语言解释。",
        "补充 1 条面向教师或学习者的教学建议。",
    ),
    evaluation_criteria=(
        "输出必须包含 corrected_text 与 error_analysis 字段。",
        "error_analysis 不得超过 3 项。",
        "敏感内容必须返回预设拒绝话术。",
    ),
    output_fields=("intent", "corrected_text", "error_analysis", "teaching_tip"),
    refusal_message="抱歉，这条内容不适合用于国际中文教学批改场景，我不能继续处理。",
    default_params={
        "target_level": "General",
        "instruction_language": "中文",
        "instruction_languages": "中文",
        "teacher_level": "experienced_teacher",
    },
    ui_label="中文批改",
)


BRIDGE_LESSON_DESIGN_SPEC = SkillSpec(
    key="bridge_lesson_design",
    name="教学设计咨询",
    description="为中文教学场景生成课堂设计方案与活动建议。",
    inputs=(
        SkillInputSpec("source_text", "string", "教学需求或问题描述"),
        SkillInputSpec(
            "instruction_language",
            "string",
            "讲解输出语言，通常跟账号的教学语言一致",
        ),
        SkillInputSpec(
            "target_level",
            "enum",
            "教学说明层级；General 表示通用表达，不强行贴合某个固定 HSK 等级",
            ("General", "HSK1", "HSK2", "Advanced"),
        ),
    ),
    implementation_logic=(
        "识别教师需求是课程规划、课堂流程设计还是活动设计。",
        "给出清晰的课堂目标与步骤化流程。",
        "提供 2-4 个可执行活动或互动策略，并说明所需材料。",
        "补充评价方式或课堂检查点。",
    ),
    evaluation_criteria=(
        "输出必须包含 lesson_goal 与 lesson_flow 字段。",
        "lesson_flow 应为可执行步骤列表。",
        "敏感内容必须返回预设拒绝话术。",
    ),
    output_fields=(
        "intent",
        "lesson_goal",
        "lesson_flow",
        "activities",
        "assessment",
        "materials",
        "teaching_tip",
    ),
    refusal_message="抱歉，这条内容不适合用于国际中文教学场景，我不能继续处理。",
    default_params={"target_level": "General", "instruction_language": "中文"},
    ui_label="教学设计咨询",
)


BRIDGE_HSK_COACHING_SPEC = SkillSpec(
    key="bridge_hsk_coaching",
    name="HSK 备考指导",
    description="提供 HSK 备考策略、资源与教学安排建议。",
    inputs=(
        SkillInputSpec("source_text", "string", "备考需求或问题描述"),
        SkillInputSpec(
            "instruction_language",
            "string",
            "讲解输出语言，通常跟账号的教学语言一致",
        ),
        SkillInputSpec(
            "target_level",
            "enum",
            "教学说明层级；General 表示通用表达，不强行贴合某个固定 HSK 等级",
            ("General", "HSK1", "HSK2", "Advanced"),
        ),
    ),
    implementation_logic=(
        "识别考试等级或备考目标。",
        "给出阶段化备考计划与重点能力分配。",
        "补充资源与模拟测试建议。",
    ),
    evaluation_criteria=(
        "输出必须包含 plan_outline 与 focus_points 字段。",
        "focus_points 不得超过 5 项。",
        "敏感内容必须返回预设拒绝话术。",
    ),
    output_fields=(
        "intent",
        "plan_outline",
        "focus_points",
        "resources",
        "mock_strategy",
        "teaching_tip",
    ),
    refusal_message="抱歉，这条内容不适合用于国际中文教学备考指导场景，我不能继续处理。",
    default_params={"target_level": "General", "instruction_language": "中文"},
    ui_label="HSK 备考指导",
)


BRIDGE_TOOL_RECOMMENDATION_SPEC = SkillSpec(
    key="bridge_tool_recommendation",
    name="数字化工具推荐",
    description="根据教学需求推荐数字化教学工具与落地步骤。",
    inputs=(
        SkillInputSpec("source_text", "string", "教学工具需求或场景描述"),
        SkillInputSpec(
            "instruction_language",
            "string",
            "讲解输出语言，通常跟账号的教学语言一致",
        ),
        SkillInputSpec(
            "target_level",
            "enum",
            "教学说明层级；General 表示通用表达，不强行贴合某个固定 HSK 等级",
            ("General", "HSK1", "HSK2", "Advanced"),
        ),
    ),
    implementation_logic=(
        "识别教学场景（课堂互动、作业管理、同步课堂等）。",
        "推荐 2-4 个工具并说明适用场景与优劣。",
        "给出落地步骤与注意事项。",
    ),
    evaluation_criteria=(
        "输出必须包含 tool_recommendations 字段。",
        "tool_recommendations 不得超过 4 项。",
        "敏感内容必须返回预设拒绝话术。",
    ),
    output_fields=(
        "intent",
        "selection_criteria",
        "tool_recommendations",
        "implementation_steps",
        "risk_notes",
    ),
    refusal_message="抱歉，这条内容不适合用于国际中文教学工具推荐场景，我不能继续处理。",
    default_params={"target_level": "General", "instruction_language": "中文"},
    ui_label="数字化工具推荐",
)


BRIDGE_POLICY_INTERPRETATION_SPEC = SkillSpec(
    key="bridge_policy_interpretation",
    name="政策法规解读",
    description="解读国际中文教育相关政策与教师标准，并给出教学影响建议。",
    inputs=(
        SkillInputSpec("source_text", "string", "政策或标准问题描述"),
        SkillInputSpec(
            "instruction_language",
            "string",
            "讲解输出语言，通常跟账号的教学语言一致",
        ),
        SkillInputSpec(
            "target_level",
            "enum",
            "教学说明层级；General 表示通用表达，不强行贴合某个固定 HSK 等级",
            ("General", "HSK1", "HSK2", "Advanced"),
        ),
    ),
    implementation_logic=(
        "概述政策核心内容与适用范围。",
        "解释对教学实践的影响，并给出合规行动建议。",
        "给出可供查阅的参考线索。",
    ),
    evaluation_criteria=(
        "输出必须包含 policy_summary 与 compliance_actions 字段。",
        "references 字段可为空，但应尽量提供。",
        "敏感内容必须返回预设拒绝话术。",
    ),
    output_fields=(
        "intent",
        "policy_summary",
        "teaching_implications",
        "compliance_actions",
        "references",
        "teaching_tip",
    ),
    refusal_message="抱歉，这条内容不适合用于国际中文教育政策解读场景，我不能继续处理。",
    default_params={"target_level": "General", "instruction_language": "中文"},
    ui_label="政策法规解读",
)


SKILL_SPECS: dict[str, SkillSpec] = {
    BRIDGE_TRANSLATE_SPEC.key: BRIDGE_TRANSLATE_SPEC,
    BRIDGE_CORRECT_SPEC.key: BRIDGE_CORRECT_SPEC,
    BRIDGE_LESSON_DESIGN_SPEC.key: BRIDGE_LESSON_DESIGN_SPEC,
    BRIDGE_HSK_COACHING_SPEC.key: BRIDGE_HSK_COACHING_SPEC,
    BRIDGE_TOOL_RECOMMENDATION_SPEC.key: BRIDGE_TOOL_RECOMMENDATION_SPEC,
    BRIDGE_POLICY_INTERPRETATION_SPEC.key: BRIDGE_POLICY_INTERPRETATION_SPEC,
}


def get_skill_spec(skill_key: str) -> SkillSpec:
    try:
        return SKILL_SPECS[skill_key]
    except KeyError as exc:
        raise ValueError(f"未知 skill: {skill_key}") from exc


def list_skill_specs() -> list[SkillSpec]:
    return list(SKILL_SPECS.values())
