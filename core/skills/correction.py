from __future__ import annotations

from typing import Generator

from .runtime import execute_skill, render_skill_result


def correct_text(
    source_text: str,
    target_level: str = "General",
    instruction_language: str = "中文",
    instruction_languages: str = "中文",
    teacher_level: str = "experienced_teacher",
) -> str:
    payload = execute_skill(
        "bridge_correct",
        source_text,
        target_level=target_level,
        instruction_language=instruction_language,
        instruction_languages=instruction_languages,
        teacher_level=teacher_level,
    )
    return render_skill_result(payload)


def correct_text_stream(
    source_text: str,
    target_level: str = "General",
    instruction_language: str = "中文",
    instruction_languages: str = "中文",
    teacher_level: str = "experienced_teacher",
    cancel_event=None,
) -> Generator[str, None, None]:
    if cancel_event is not None and cancel_event.is_set():
        return

    yield "正在批改，请稍等...\n"
    payload = execute_skill(
        "bridge_correct",
        source_text,
        target_level=target_level,
        instruction_language=instruction_language,
        instruction_languages=instruction_languages,
        teacher_level=teacher_level,
    )
    if cancel_event is not None and cancel_event.is_set():
        return
    yield render_skill_result(payload)
