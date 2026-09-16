#!/usr/bin/env python3
"""Regression checks for conversational module routing without external model calls."""

from types import SimpleNamespace
from unittest.mock import patch

from core import assistant_service
from core.ai_agent import _build_messages, _build_system_prompt


def fake_profile(*, role: str = "student"):
    is_student = role == "student"
    return SimpleNamespace(
        account_id="conversation_test",
        account_role=role,
        is_student=is_student,
        is_teacher=not is_student,
        display_name="测试用户",
        student_level="hsk2",
        student_level_label="HSK 2",
        learning_goal_label="在上海生活",
        instruction_language="English" if is_student else "中文",
        teaching_languages_display="中文、English",
        teacher_role_label="一线教师",
        teacher_level="experienced_teacher",
        teacher_role="experienced_teacher",
        region="上海",
        school_stage="高校",
    )


if __name__ == "__main__":
    conversational_skill_keys = {
        "bridge_lesson_design",
        "bridge_translate",
        "bridge_correct",
        "bridge_hsk_coaching",
        "bridge_tool_recommendation",
        "bridge_policy_interpretation",
    }
    configured = {
        skill.key
        for skill in assistant_service.ASSISTANT_SKILLS
        if skill.mode == "advisor" and skill.prompt_prefix
    }
    assert conversational_skill_keys <= configured

    captured = {}

    def fake_generate(user_input, **kwargs):
        captured["user_input"] = user_input
        captured.update(kwargs)
        return "Hello! How can I help with your HSK study today?"

    with patch.object(assistant_service, "generate_response", fake_generate):
        reply = assistant_service.run_assistant_turn(
            skill_key="bridge_hsk_coaching",
            text="hello?",
            profile=fake_profile(),
            history=[
                {"role": "user", "content": "I am preparing for HSK 2."},
                {"role": "assistant", "content": "What would you like to practise?"},
                {"role": "user", "content": "hello?"},
            ],
        )

    assert reply.startswith("Hello!")
    assert captured["user_input"] == "hello?"
    assert captured["history"] == [
        ("I am preparing for HSK 2.", "What would you like to practise?")
    ]
    assert "不能自动重复整套备考模板" in captured["system_extension"]

    profile = fake_profile()
    context = SimpleNamespace(
        learner_level="HSK 2",
        confidence="high",
        teaching_goal="日常交流",
        evidence="用户画像",
    )
    prompt = _build_system_prompt("无", profile, context, "测试模块指引")
    assert "当前功能模块只限定你的专业能力范围" in prompt
    assert "测试模块指引" in prompt
    messages = _build_messages(
        prompt,
        "hello?",
        [("I need a plan.", "How much time do you have?")],
    )
    assert [item["role"] for item in messages] == ["system", "user", "assistant", "user"]
    assert messages[-1]["content"] == "hello?"

    print("[OK] conversational module routing regressions passed")
