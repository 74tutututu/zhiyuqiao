"""Skill modules for ZhiYuQiao.

skills 用于承载可复用的能力模块（如翻译、纠错、教学设计等），可被网页界面和 API 统一调用。
"""

from .correction import correct_text, correct_text_stream
from .runtime import execute_skill, execute_skill_stream, list_skill_summaries
from .translation import translate_text, translate_text_stream

__all__ = [
    "correct_text",
    "correct_text_stream",
    "execute_skill",
    "execute_skill_stream",
    "list_skill_summaries",
    "translate_text",
    "translate_text_stream",
]
