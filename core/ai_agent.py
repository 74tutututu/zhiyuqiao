import os
from dotenv import load_dotenv
from openai import OpenAI
from .retriever import get_relevant_info

# 加载环境变量
load_dotenv()

# 初始化 DeepSeek 客户端
client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

REVIEW_NOTICE = "\n\n---\n⚠️ **人工审核提示**：本内容由 AI 生成，涉及具体教学决策或政策解读时，请结合实际教学环境及官方最新文件进行核实。"


def _build_system_prompt(local_context, hsk_level="不限"):
    """构建 System Prompt"""
    hsk_part = (
        f"用户当前关注的 HSK 等级：{hsk_level}。请据此调整回复内容的难度和针对性。"
        if hsk_level != "不限"
        else ""
    )
    return f"""
# 角色
你是一位具备国际中文教育（博士）与教育技术学（硕士）双背景的国际多语言数字化教育顾问。你拥有10年HSK教学经验，使命是提供数字化教学解决方案。

## 核心工作流 (All 工作流)
1. 初步判断：分析用户需求是否属于国际中文教育数字化范畴。
2. 需求分类：区分是教学资源、工具推荐、政策咨询还是技术方案。
3. 精准服务：结合本地参考资料给出专业建议。

## 限制与准则
- 仅回答与国际中文教育数字化教学相关的问题。
- 遵循地域适配优先和开源工具优先原则。
- 拒绝涉及宗教/政治敏感内容。
- 本地参考资料：{local_context}
{hsk_part}
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


def generate_response(user_input, history=None, hsk_level="不限"):
    """非流式生成回复（兼容旧调用）"""
    local_context = get_relevant_info(user_input, hsk_level)
    system_prompt = _build_system_prompt(local_context, hsk_level)
    messages = _build_messages(system_prompt, user_input, history)

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content + REVIEW_NOTICE
    except Exception as e:
        return f"⚠️ 顾问系统暂时无法响应，请稍后重试。\n\n错误详情：{str(e)}"


def generate_response_stream(user_input, history=None, hsk_level="不限", cancel_event=None):
    """流式生成回复 - 逐步 yield 累积文本，支持通过 cancel_event 中止"""
    if isinstance(user_input, list):
        user_input = " ".join(str(item) for item in user_input)
    user_input = str(user_input)
    local_context = get_relevant_info(user_input, hsk_level)
    system_prompt = _build_system_prompt(local_context, hsk_level)
    messages = _build_messages(system_prompt, user_input, history)

    try:
        stream = client.chat.completions.create(
            model="deepseek-chat",
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
