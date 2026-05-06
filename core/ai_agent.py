from __future__ import annotations

from .account_profiles import get_teacher_profile
from .llm_client import DEEPSEEK_MODEL, client
from .retriever import get_relevant_info
from .teaching_context import analyze_teaching_context

REVIEW_NOTICE = "\n\n---\n⚠️ **人工审核提示**：本内容由 AI 生成，涉及具体教学决策或政策解读时，请结合实际教学环境及官方最新文件进行核实。"

TEACHER_ROLE_GUIDANCE = {
    "novice_teacher": "优先给出清晰步骤、可直接照搬的课堂组织方式，并减少不必要术语。",
    "experienced_teacher": "优先给出方案对比、课堂调度要点和差异化教学建议。",
    "researcher": "优先给出框架化分析、评估指标、研究视角和参考依据线索。",
}


def _build_system_prompt(local_context, teacher_profile, teaching_context):
    """构建 System Prompt。"""
    role_guidance = TEACHER_ROLE_GUIDANCE.get(
        teacher_profile.teacher_role,
        "根据教师场景提供专业、清晰且可执行的建议。",
    )
    return f"""
# 角色
你是一位具备国际中文教育（博士）与教育技术学（硕士）双背景的国际多语言数字化教育顾问。你拥有10年HSK教学经验，使命是提供数字化教学解决方案。

## 当前账号画像
- 当前账号：{teacher_profile.display_name}
- 教学语言：{teacher_profile.teaching_languages_display}
- 首选教学语言：{teacher_profile.instruction_language}
- 教师角色：{teacher_profile.teacher_role_label}
- 区域/场景：{teacher_profile.region or "通用"}
- 学段：{teacher_profile.school_stage or "综合"}

## 当前教学上下文
- 学生水平判断：{teaching_context.learner_level}
- 判断置信度：{teaching_context.confidence}
- 教学目标：{teaching_context.teaching_goal}
- 判断线索：{teaching_context.evidence or "未提供明显线索"}

## 限制与准则
- 仅回答与国际中文教育数字化教学相关的问题。
- 遵循地域适配优先和开源工具优先原则。
- 拒绝涉及宗教/政治敏感内容。
- 主要使用 {teacher_profile.instruction_language} 回答；如用户明确要求其他目标语言，优先服从用户要求。
- 当前账号可使用的教学语言包括：{teacher_profile.teaching_languages_display}。
- 如需展示中文例句、词语或句型，可以保留中文并做对应说明。
- {role_guidance}
- 如果学生水平线索不足或置信度较低，按通用教学水准回答，不要假设固定班型或固定 HSK 等级。
- 回答优先给出可执行建议；只有在教师角色或问题明确需要时，再展开学术化分析。
- 本地参考资料：{local_context}
"""


def _build_messages(system_prompt, user_input, history=None):
    """将历史对话 + 当前输入组装为 messages 列表"""
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for user_msg, bot_msg in history:
            if user_msg:
                messages.append({"role": "user", "content": user_msg})
            if bot_msg:
                # 去掉审核提示避免污染上下文
                clean = bot_msg.split("\n\n---\n⚠️")[0] if "\n\n---\n⚠️" in bot_msg else bot_msg
                messages.append({"role": "assistant", "content": clean})
    messages.append({"role": "user", "content": user_input})
    return messages


def generate_response(user_input, history=None, hsk_level="自动判断", account_id=None):
    """非流式生成回复（兼容旧调用）"""
    teacher_profile = get_teacher_profile(account_id)
    teaching_context = analyze_teaching_context(
        user_input,
        history=history,
        learner_level_hint=hsk_level,
    )
    local_context = get_relevant_info(
        user_input,
        teaching_context.retrieval_hsk_level,
    )
    system_prompt = _build_system_prompt(local_context, teacher_profile, teaching_context)
    messages = _build_messages(system_prompt, user_input, history)

    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content + REVIEW_NOTICE
    except Exception as e:
        return f"⚠️ 顾问系统暂时无法响应，请稍后重试。\n\n错误详情：{str(e)}"


def generate_response_stream(
    user_input,
    history=None,
    hsk_level="自动判断",
    cancel_event=None,
    account_id=None,
):
    """流式生成回复 - 逐步 yield 累积文本，支持通过 cancel_event 中止"""
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    user_input = str(user_input)
    teacher_profile = get_teacher_profile(account_id)
    teaching_context = analyze_teaching_context(
        user_input,
        history=history,
        learner_level_hint=hsk_level,
    )
    local_context = get_relevant_info(
        user_input,
        teaching_context.retrieval_hsk_level,
    )
    system_prompt = _build_system_prompt(local_context, teacher_profile, teaching_context)
    messages = _build_messages(system_prompt, user_input, history)

    try:
        stream = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            temperature=0.3,
            stream=True,
        )
        accumulated = ""
        for chunk in stream:
            if cancel_event is not None and cancel_event.is_set():
                # 用户中止生成
                yield accumulated + "\n\n---\n🛑 **生成已被用户终止。**"
                return
            if chunk.choices and chunk.choices[0].delta.content:
                accumulated += chunk.choices[0].delta.content
                yield accumulated
        # 流结束后追加审核提示
        yield accumulated + REVIEW_NOTICE
    except Exception as e:
        yield f"⚠️ 顾问系统暂时无法响应，请稍后重试。\n\n错误详情：{str(e)}"
