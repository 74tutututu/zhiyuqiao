from __future__ import annotations

import json
import logging
import re
from typing import Any, Generator

from pypinyin import Style, lazy_pinyin

from ..llm_client import DEEPSEEK_MODEL, client
from ..skill_routing import build_skill_knowledge_context
from .specs import SkillSpec, get_skill_spec, list_skill_specs

logger = logging.getLogger(__name__)

SENSITIVE_PATTERNS = (
    "政治",
    "宗教",
    "暴力",
    "恐怖",
    "炸弹",
    "枪支",
    "毒品",
    "色情",
    "极端主义",
    "自杀",
    "赌博",
    "money laundering",
    "terror",
    "porn",
)

CHINESE_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")

TEACHER_LEVEL_GUIDANCE = {
    "novice_teacher": "解释尽量清晰直接，优先给可立即使用的表达与步骤。",
    "experienced_teacher": "解释保持专业与简洁，并补充课堂应用建议。",
    "researcher": "解释可以更框架化，适当补充分析视角和评价线索。",
}


def _contains_sensitive_content(text: Any) -> bool:
    if text is None:
        return False
    if isinstance(text, (list, tuple)):
        flattened = " ".join(str(item) for item in text)
        lowered = flattened.lower()
    else:
        lowered = str(text).lower()
    return any(pattern.lower() in lowered for pattern in SENSITIVE_PATTERNS)


def _json_contract_lines(spec: SkillSpec) -> str:
    fields = "\n".join(f'- "{field}"' for field in spec.output_fields)
    return (
        "你必须只返回一个 JSON 对象，不要使用 Markdown 代码块。\n"
        "输出 JSON 至少包含以下字段：\n"
        f"{fields}"
    )


def _format_spec_prompt(spec: SkillSpec, params: dict[str, Any]) -> str:
    input_lines = []
    for input_spec in spec.inputs:
        value = params.get(input_spec.name, spec.default_params.get(input_spec.name, ""))
        choices = f" 允许值: {', '.join(input_spec.choices)}。" if input_spec.choices else ""
        input_lines.append(
            f"- `{input_spec.name}`: {value}。{input_spec.description}.{choices}"
        )
    logic_lines = "\n".join(
        f"{index}. {step}" for index, step in enumerate(spec.implementation_logic, 1)
    )
    eval_lines = "\n".join(f"- [ ] {item}" for item in spec.evaluation_criteria)
    knowledge_context = str(params.get("knowledge_context", "")).strip()
    routing_note = str(params.get("routing_note", "")).strip()
    instruction_language = str(params.get("instruction_language", spec.default_params.get("instruction_language", "中文"))).strip() or "中文"
    instruction_languages = str(params.get("instruction_languages", instruction_language)).strip() or instruction_language
    teacher_level = str(params.get("teacher_level", "experienced_teacher")).strip() or "experienced_teacher"
    teacher_level_note = TEACHER_LEVEL_GUIDANCE.get(
        teacher_level,
        "解释应兼顾专业性和可执行性。",
    )
    knowledge_block = knowledge_context if knowledge_context else "无"
    routing_block = routing_note if routing_note else "无"

    return f"""
# Skill: {spec.name}

## Description
{spec.description}

## Inputs
{chr(10).join(input_lines)}

## Implementation Logic
{logic_lines}

## Evaluation Criteria
{eval_lines}

## Knowledge Routing
- routing: {routing_block}

## Knowledge Context
{knowledge_block}

## Safety
- 如果用户输入包含敏感内容，必须返回拒绝结果。
- 拒绝结果中的 `message` 必须严格等于：{spec.refusal_message}

## Additional Preferences
- `instruction_language` 指定结果的讲解语言，请优先使用该语言组织 `teaching_note` / `teaching_tip`。
- 当前账号可用教学语言：{instruction_languages}。
- 当前账号的首选教学语言：{instruction_language}。
- 当前账号的教师水平：{teacher_level}。请遵循：{teacher_level_note}
- 如果用户提问语言明显不同于 `instruction_language`，优先使用用户明确要求的目标语言或提问语言作答，必要时再补充教学语言说明。
- 对翻译类任务，如果用户在原问题中明确指定了“用某某语言翻译”，必须优先服从这个目标语言要求。
- 如果目标输出不是中文，则不必强行生成拼音；只有在输出包含中文时才补拼音。

## Output Contract
{_json_contract_lines(spec)}
""".strip()


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("模型未返回有效 JSON 对象")
    return json.loads(text[start : end + 1])


def _normalize_vocabulary_notes(notes: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(notes, list):
        return normalized

    for note in notes[:3]:
        if isinstance(note, dict):
            word = str(note.get("word", "")).strip()
            explanation = str(note.get("explanation", "")).strip()
        else:
            word = ""
            explanation = str(note).strip()
        if word or explanation:
            normalized.append({"word": word, "explanation": explanation})
    return normalized


def _normalize_error_analysis(items: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(items, list):
        return normalized

    for item in items[:3]:
        if isinstance(item, dict):
            normalized.append(
                {
                    "issue": str(item.get("issue", "")).strip(),
                    "explanation": str(item.get("explanation", "")).strip(),
                    "suggestion": str(item.get("suggestion", "")).strip(),
                }
            )
        else:
            normalized.append(
                {
                    "issue": str(item).strip(),
                    "explanation": "",
                    "suggestion": "",
                }
            )
    return normalized


def _text_to_pinyin(text: str) -> str:
    pieces: list[str] = []
    for char in text:
        if char == "\n":
            pieces.append("\n")
        elif CHINESE_CHAR_RE.match(char):
            pieces.append(lazy_pinyin(char, style=Style.TONE, neutral_tone_with_five=True)[0])
        elif char.isspace():
            if not pieces or pieces[-1] != " ":
                pieces.append(" ")
        else:
            pieces.append(char)

    rendered = " ".join(piece for piece in pieces if piece != "\n")
    rendered = re.sub(r"\s+([,.;:!?，。；：！？])", r"\1", rendered)
    rendered = rendered.replace(" \n ", "\n").replace(" \n", "\n").replace("\n ", "\n")
    return re.sub(r" {2,}", " ", rendered).strip()


def _refusal_payload(spec: SkillSpec) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "skill": spec.key,
        "status": "refused",
        "intent": "refusal",
        "message": spec.refusal_message,
    }
    if spec.key == "bridge_translate":
        payload.update(
            {
                "translation": "",
                "pinyin": "",
                "vocabulary_notes": [],
                "teaching_note": "",
            }
        )
    elif spec.key == "bridge_correct":
        payload.update(
            {
                "corrected_text": "",
                "error_analysis": [],
                "teaching_tip": "",
            }
        )
    return payload


def _error_payload(spec: SkillSpec, exc: Exception) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "skill": spec.key,
        "status": "error",
        "intent": "error",
        "message": f"{spec.name} 暂时不可用，请稍后重试。",
        "error_detail": str(exc),
    }
    if spec.key == "bridge_translate":
        payload.update(
            {
                "translation": "",
                "pinyin": "",
                "vocabulary_notes": [],
                "teaching_note": "",
            }
        )
    elif spec.key == "bridge_correct":
        payload.update(
            {
                "corrected_text": "",
                "error_analysis": [],
                "teaching_tip": "",
            }
        )
    return payload


def _normalize_result(spec: SkillSpec, model_data: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    base: dict[str, Any] = {
        "skill": spec.key,
        "status": "ok",
        "intent": str(model_data.get("intent", "task_execution")).strip() or "task_execution",
        "target_level": str(params.get("target_level", spec.default_params.get("target_level", ""))),
    }

    if spec.key == "bridge_translate":
        translation = str(model_data.get("translation", "")).strip()
        has_chinese = bool(CHINESE_CHAR_RE.search(translation))
        base.update(
            {
                "translation": translation,
                "pinyin": _text_to_pinyin(translation) if translation and has_chinese else "",
                "vocabulary_notes": _normalize_vocabulary_notes(model_data.get("vocabulary_notes")),
                "teaching_note": str(model_data.get("teaching_note", "")).strip(),
            }
        )
        return base

    if spec.key == "bridge_correct":
        base.update(
            {
                "corrected_text": str(model_data.get("corrected_text", "")).strip(),
                "error_analysis": _normalize_error_analysis(model_data.get("error_analysis")),
                "teaching_tip": str(model_data.get("teaching_tip", "")).strip(),
            }
        )
        return base

    return {**base, **model_data}


def _call_skill_model(spec: SkillSpec, source_text: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        if _contains_sensitive_content(source_text):
            return _refusal_payload(spec)

        system_prompt = _format_spec_prompt(spec, params)
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(source_text)},
            ],
            temperature=0.2,
        )
        payload = _extract_json_object(response.choices[0].message.content or "{}")
        if str(payload.get("intent", "")).strip().lower() == "refusal":
            return _refusal_payload(spec)
        return _normalize_result(spec, payload, params)
    except Exception as exc:
        logger.exception("Skill execution failed for %s", spec.key)
        return _error_payload(spec, exc)


def _stream_skill_model(
    spec: SkillSpec,
    source_text: str,
    params: dict[str, Any],
    cancel_event=None,
) -> Generator[str, None, None]:
    try:
        if _contains_sensitive_content(source_text):
            yield render_skill_result(_refusal_payload(spec))
            return

        yield f"正在执行 {spec.name}...\n"
        stream = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": _format_spec_prompt(spec, params)},
                {"role": "user", "content": str(source_text)},
            ],
            temperature=0.2,
            stream=True,
        )
        accumulated = ""
        for chunk in stream:
            if cancel_event is not None and cancel_event.is_set():
                yield f"正在执行 {spec.name}...\n\n---\n🛑 **Skill 执行已被用户终止。**"
                return
            if chunk.choices and chunk.choices[0].delta.content:
                accumulated += chunk.choices[0].delta.content

        payload = _extract_json_object(accumulated or "{}")
        if str(payload.get("intent", "")).strip().lower() == "refusal":
            normalized = _refusal_payload(spec)
        else:
            normalized = _normalize_result(spec, payload, params)
        yield render_skill_result(normalized)
    except Exception as exc:
        logger.exception("Skill streaming failed for %s", spec.key)
        yield render_skill_result(_error_payload(spec, exc))


def execute_skill(skill_key: str, source_text: str, **params: Any) -> dict[str, Any]:
    spec = get_skill_spec(skill_key)
    merged_params = {**spec.default_params, **params}
    knowledge_context, routing = build_skill_knowledge_context(
        skill_key,
        source_text,
        hsk_level=str(merged_params.get("hsk_level", "不限")),
    )
    merged_params["knowledge_context"] = knowledge_context
    merged_params["routing_note"] = f"{routing.intent} ({routing.source})"
    return _call_skill_model(spec, source_text, merged_params)


def execute_skill_stream(
    skill_key: str,
    source_text: str,
    cancel_event=None,
    **params: Any,
) -> Generator[str, None, None]:
    spec = get_skill_spec(skill_key)
    merged_params = {**spec.default_params, **params}
    knowledge_context, routing = build_skill_knowledge_context(
        skill_key,
        source_text,
        hsk_level=str(merged_params.get("hsk_level", "不限")),
    )
    merged_params["knowledge_context"] = knowledge_context
    merged_params["routing_note"] = f"{routing.intent} ({routing.source})"
    yield from _stream_skill_model(spec, source_text, merged_params, cancel_event=cancel_event)


def format_skill_result(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_kv_lines(items: list[tuple[str, str]]) -> str:
    lines = [f"**{label}**\n{value}" for label, value in items if value]
    return "\n\n".join(lines)


def _render_list(value: Any, max_items: int | None = None) -> str:
    if isinstance(value, str):
        value = value.strip()
        return value if value else "无"
    if not isinstance(value, list):
        return "无"

    items = value[:max_items] if max_items else value
    rendered = []
    for item in items:
        if isinstance(item, dict):
            rendered.append(", ".join(
                str(v).strip() for v in item.values() if str(v).strip()
            ))
        else:
            rendered.append(str(item).strip())
    rendered = [r for r in rendered if r]
    return "\n".join(f"- {r}" for r in rendered) if rendered else "无"


def render_skill_result(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return str(payload)

    skill = str(payload.get("skill", "")).strip()
    status = str(payload.get("status", "")).strip().lower()
    message = str(payload.get("message", "")).strip()
    error_detail = str(payload.get("error_detail", "")).strip()

    if skill == "bridge_translate":
        title = "🌐 翻译结果"
        if status in {"refused", "error"}:
            body = _render_kv_lines(
                [
                    ("状态", "已拒绝" if status == "refused" else "执行失败"),
                    ("提示", message),
                    ("详情", error_detail),
                ]
            )
            return f"### {title}\n\n{body}".strip()

        vocabulary_notes = payload.get("vocabulary_notes") or []
        notes_text = "\n".join(
            f"- **{item.get('word', '').strip()}**：{item.get('explanation', '').strip()}"
            for item in vocabulary_notes
            if isinstance(item, dict) and (item.get("word") or item.get("explanation"))
        )
        if not notes_text:
            notes_text = "无"

        translation = str(payload.get("translation", "")).strip() or "无"
        pinyin = str(payload.get("pinyin", "")).strip()
        teaching_note = str(payload.get("teaching_note", "")).strip()

        sections = [
            f"### {title}",
            f"**译文**\n{translation}",
        ]
        if pinyin:
            sections.append(f"**拼音**\n{pinyin}")
        if notes_text != "无":
            sections.append(f"**核心词汇**\n{notes_text}")
        if teaching_note:
            sections.append(f"**教学提示**\n{teaching_note}")
        return "\n\n".join(sections).strip()

    if skill == "bridge_correct":
        title = "📝 批改结果"
        if status in {"refused", "error"}:
            body = _render_kv_lines(
                [
                    ("状态", "已拒绝" if status == "refused" else "执行失败"),
                    ("提示", message),
                    ("详情", error_detail),
                ]
            )
            return f"### {title}\n\n{body}".strip()

        error_analysis = payload.get("error_analysis") or []
        analysis_text = "\n".join(
            f"- **{item.get('issue', '').strip()}**：{item.get('explanation', '').strip()}"
            + (
                f"（建议：{item.get('suggestion', '').strip()}）"
                if isinstance(item, dict) and item.get("suggestion")
                else ""
            )
            for item in error_analysis
            if isinstance(item, dict) and (item.get("issue") or item.get("explanation") or item.get("suggestion"))
        )
        if not analysis_text:
            analysis_text = "无"

        corrected_text = str(payload.get("corrected_text", "")).strip() or "无"
        teaching_tip = str(payload.get("teaching_tip", "")).strip() or "无"

        return (
            f"### {title}\n\n"
            f"**修改后文本**\n{corrected_text}\n\n"
            f"**错误分析**\n{analysis_text}\n\n"
            f"**教学建议**\n{teaching_tip}"
        ).strip()

    if skill == "bridge_lesson_design":
        title = "📚 教学设计建议"
        if status in {"refused", "error"}:
            body = _render_kv_lines(
                [
                    ("状态", "已拒绝" if status == "refused" else "执行失败"),
                    ("提示", message),
                    ("详情", error_detail),
                ]
            )
            return f"### {title}\n\n{body}".strip()

        return (
            f"### {title}\n\n"
            "以下方案可直接用于备课或课堂调整：\n\n"
            f"**课堂目标**\n{str(payload.get('lesson_goal', '')).strip() or '无'}\n\n"
            f"**课堂流程**\n{_render_list(payload.get('lesson_flow'))}\n\n"
            f"**活动建议**\n{_render_list(payload.get('activities'))}\n\n"
            f"**评价方式**\n{str(payload.get('assessment', '')).strip() or '无'}\n\n"
            f"**所需材料**\n{str(payload.get('materials', '')).strip() or '无'}\n\n"
            f"**教学提示**\n{str(payload.get('teaching_tip', '')).strip() or '无'}"
        ).strip()

    if skill == "bridge_hsk_coaching":
        title = "🎯 HSK 备考指导"
        if status in {"refused", "error"}:
            body = _render_kv_lines(
                [
                    ("状态", "已拒绝" if status == "refused" else "执行失败"),
                    ("提示", message),
                    ("详情", error_detail),
                ]
            )
            return f"### {title}\n\n{body}".strip()

        return (
            f"### {title}\n\n"
            "下面是分阶段的备考安排，可按周或按课时调整：\n\n"
            f"**备考计划**\n{_render_list(payload.get('plan_outline'))}\n\n"
            f"**重点能力**\n{_render_list(payload.get('focus_points'), max_items=5)}\n\n"
            f"**资源建议**\n{_render_list(payload.get('resources'))}\n\n"
            f"**模拟策略**\n{str(payload.get('mock_strategy', '')).strip() or '无'}\n\n"
            f"**教学提示**\n{str(payload.get('teaching_tip', '')).strip() or '无'}"
        ).strip()

    if skill == "bridge_tool_recommendation":
        title = "🧰 数字化工具推荐"
        if status in {"refused", "error"}:
            body = _render_kv_lines(
                [
                    ("状态", "已拒绝" if status == "refused" else "执行失败"),
                    ("提示", message),
                    ("详情", error_detail),
                ]
            )
            return f"### {title}\n\n{body}".strip()

        return (
            f"### {title}\n\n"
            "基于你的场景，以下工具更适配教学落地：\n\n"
            f"**选型标准**\n{_render_list(payload.get('selection_criteria'))}\n\n"
            f"**工具推荐**\n{_render_list(payload.get('tool_recommendations'), max_items=4)}\n\n"
            f"**落地步骤**\n{_render_list(payload.get('implementation_steps'))}\n\n"
            f"**风险提示**\n{str(payload.get('risk_notes', '')).strip() or '无'}"
        ).strip()

    if skill == "bridge_policy_interpretation":
        title = "📜 政策法规解读"
        if status in {"refused", "error"}:
            body = _render_kv_lines(
                [
                    ("状态", "已拒绝" if status == "refused" else "执行失败"),
                    ("提示", message),
                    ("详情", error_detail),
                ]
            )
            return f"### {title}\n\n{body}".strip()

        return (
            f"### {title}\n\n"
            "为便于课堂与项目落地，整理出以下要点：\n\n"
            f"**政策摘要**\n{str(payload.get('policy_summary', '')).strip() or '无'}\n\n"
            f"**教学影响**\n{str(payload.get('teaching_implications', '')).strip() or '无'}\n\n"
            f"**合规行动**\n{_render_list(payload.get('compliance_actions'))}\n\n"
            f"**参考线索**\n{_render_list(payload.get('references'))}\n\n"
            f"**教学提示**\n{str(payload.get('teaching_tip', '')).strip() or '无'}"
        ).strip()

    return format_skill_result(payload)


def maybe_render_skill_result(raw_text: str) -> str:
    text = str(raw_text).strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            payload = json.loads(text)
        except Exception:
            return raw_text
        return render_skill_result(payload)
    return raw_text


def list_skill_summaries() -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for spec in list_skill_specs():
        summaries.append(
            {
                "key": spec.key,
                "name": spec.name,
                "ui_label": spec.ui_label or spec.name,
                "description": spec.description,
                "inputs": [
                    {
                        "name": item.name,
                        "type": item.type,
                        "description": item.description,
                        "choices": list(item.choices),
                    }
                    for item in spec.inputs
                ],
                "evaluation_criteria": list(spec.evaluation_criteria),
            }
        )
    return summaries
