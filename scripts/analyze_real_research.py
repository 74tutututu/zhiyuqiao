#!/usr/bin/env python3
"""Parse and audit the user-supplied real research records.

Raw Markdown files are treated as immutable source evidence.  This script emits
anonymous, analysis-ready CSV files and a compact JSON/Markdown audit summary.
It deliberately excludes observer and reviewer names from public outputs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import statistics
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable


PROJECT = Path(__file__).resolve().parents[1]
RAW_ROOT = PROJECT / "调研数据" / "调研数据"
QUESTIONNAIRE_DIR = RAW_ROOT / "问卷回复"
INTERVIEW_DIR = RAW_ROOT / "访谈记录"
TASK_DIR = RAW_ROOT / "任务测试记录"
ANON_DIR = PROJECT / "05_匿名化数据"
ANALYSIS_DIR = PROJECT / "06_数据分析"
ANALYSIS_DATE = date(2026, 8, 28)
DATE_CORRECTION_NOTE = "经数据提供者确认，原记录日期统一前移7天并保持先后顺序。"


def natural_key(path: Path) -> tuple[Any, ...]:
    return tuple(int(part) if part.isdigit() else part for part in re.split(r"(\d+)", path.name))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def split_multi(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[、,，;；]", value) if item.strip()]


def to_number(value: str) -> int | float | None:
    text = value.strip()
    if text in {"", "NA", "N/A", "不适用"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def mean(values: Iterable[int | float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(statistics.fmean(clean), 3) if clean else None


def median(values: Iterable[int | float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(statistics.median(clean), 3) if clean else None


def sample_sd(values: Iterable[int | float | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(statistics.stdev(clean), 3) if len(clean) >= 2 else None


def percent(part: int | float, whole: int | float) -> float | None:
    return round(float(part) / float(whole), 4) if whole else None


def counter_rows(counter: Counter[str], total: int) -> list[dict[str, Any]]:
    return [
        {"item": item, "count": count, "rate": percent(count, total)}
        for item, count in counter.most_common()
    ]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not fieldnames:
        raise ValueError(f"Cannot infer columns for empty CSV: {path}")
    columns = fieldnames or list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_questionnaires() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    exact_hashes: Counter[str] = Counter()
    for path in sorted(QUESTIONNAIRE_DIR.glob("REAL-*.md"), key=natural_key):
        text = read_text(path)
        answers = {
            int(number): value.strip()
            for number, value in re.findall(r"(?m)^Q(\d+)\..*?\n答案：([^\r\n]*)", text)
        }
        missing = [number for number in range(33) if number not in answers or not answers[number]]
        tried = answers.get(21) == "已试用"
        trial_consistent = all(
            (to_number(answers.get(number, "")) is not None) if tried else answers.get(number) == "不适用"
            for number in range(22, 29)
        )
        valid = (
            answers.get(0) == "同意"
            and answers.get(1) == "同意"
            and not missing
            and trial_consistent
            and len(split_multi(answers.get(17, ""))) <= 3
            and len(split_multi(answers.get(18, ""))) <= 3
            and len(split_multi(answers.get(20, ""))) <= 3
        )
        answer_fingerprint = hashlib.sha256(
            "\u241f".join(answers.get(number, "") for number in range(33)).encode("utf-8")
        ).hexdigest()
        exact_hashes[answer_fingerprint] += 1
        row: dict[str, Any] = {
            "record_id": path.stem,
            "data_class": "REAL_SUPPLIED",
            "valid_record": 1 if valid else 0,
            "quality_issue": "" if valid else ";".join(
                filter(None, [
                    f"missing:{','.join(map(str, missing))}" if missing else "",
                    "consent" if answers.get(0) != "同意" or answers.get(1) != "同意" else "",
                    "trial_inconsistent" if not trial_consistent else "",
                    "selection_limit" if any(
                        len(split_multi(answers.get(number, ""))) > 3 for number in (17, 18, 20)
                    ) else "",
                ])
            ),
        }
        for number in range(33):
            row[f"q{number}"] = answers.get(number, "")
        rows.append(row)

    valid_rows = [row for row in rows if row["valid_record"] == 1]
    trial_rows = [row for row in valid_rows if row["q21"] == "已试用"]
    q_mean = {
        f"q{number}_mean": mean(to_number(row[f"q{number}"]) for row in valid_rows)
        for number in range(9, 17)
    }
    trial_mean = {
        f"q{number}_mean": mean(to_number(row[f"q{number}"]) for row in trial_rows)
        for number in range(22, 29)
    }
    summary = {
        "received": len(rows),
        "valid": len(valid_rows),
        "invalid": len(rows) - len(valid_rows),
        "trial_count": len(trial_rows),
        "trial_rate": percent(len(trial_rows), len(valid_rows)),
        "exact_duplicate_groups": sum(1 for count in exact_hashes.values() if count > 1),
        "exact_duplicate_records": sum(count for count in exact_hashes.values() if count > 1),
        "background": {
            "mother_tongue": counter_rows(Counter(row["q3"] for row in valid_rows), len(valid_rows)),
            "hsk_level": counter_rows(Counter(row["q4"] for row in valid_rows), len(valid_rows)),
            "identity": counter_rows(Counter(row["q6"] for row in valid_rows), len(valid_rows)),
            "shanghai_experience": counter_rows(Counter(row["q7"] for row in valid_rows), len(valid_rows)),
        },
        "need_scale_means": q_mean,
        "trial_scale_means": trial_mean,
        "preferences": {
            "scenes": counter_rows(Counter(item for row in valid_rows for item in split_multi(row["q17"])), len(valid_rows)),
            "supports": counter_rows(Counter(item for row in valid_rows for item in split_multi(row["q18"])), len(valid_rows)),
            "formats": counter_rows(Counter(row["q19"] for row in valid_rows), len(valid_rows)),
            "ai_priorities": counter_rows(Counter(item for row in valid_rows for item in split_multi(row["q20"])), len(valid_rows)),
            "suggestions": counter_rows(Counter(row["q32"] for row in valid_rows), len(valid_rows)),
        },
        "knowledge_checks": {
            "q30_correct": sum(row["q30"].strip().upper().startswith("B") for row in valid_rows),
            "q30_rate": percent(sum(row["q30"].strip().upper().startswith("B") for row in valid_rows), len(valid_rows)),
            "q31_correct": sum(row["q31"].strip().upper().startswith("B") for row in valid_rows),
            "q31_rate": percent(sum(row["q31"].strip().upper().startswith("B") for row in valid_rows), len(valid_rows)),
        },
    }
    return rows, summary


def parse_key_value_record(path: Path) -> dict[str, str]:
    row: dict[str, str] = {}
    for line in read_text(path).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if re.fullmatch(r"[A-Za-z0-9_]+", key):
            row[key] = value.strip()
    return row


def parse_tasks(questionnaire_ids: set[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(TASK_DIR.glob("TASK-*.md"), key=natural_key):
        source = parse_key_value_record(path)
        test_date = datetime.strptime(source["test_date"], "%Y-%m-%d").date()
        valid = (
            source.get("consent") == "同意"
            and source.get("age_18_plus") == "是"
            and source.get("quality_flag") == "PASS"
            and source.get("source_questionnaire_id") in questionnaire_ids
        )
        public_keys = [
            "task_record_id", "source_questionnaire_id", "test_date", "group", "hsk_level",
            "pre_culture", "pre_judgement_answer", "pre_open_score_0_2", "completion_sec",
            "help_count", "system_or_network_error", "over_8min", "post_culture",
            "post_choice_answer", "post_open_score_0_3", "task_correct_0_1", "culture_gain",
            "relevance_1_5_or_NA", "cultural_clarity_1_5_or_NA",
            "language_accessibility_1_5_or_NA", "usability_1_5_or_NA", "trust_1_5_or_NA",
            "reuse_intent_1_5_or_NA", "quality_flag",
        ]
        row: dict[str, Any] = {key: source.get(key, "") for key in public_keys}
        row["valid_record"] = 1 if valid else 0
        row["future_date_flag"] = 1 if test_date > ANALYSIS_DATE else 0
        rows.append(row)

    valid_rows = [row for row in rows if row["valid_record"] == 1]
    summaries: dict[str, Any] = {}
    for group in ("智语桥组", "常规检索组"):
        group_rows = [row for row in valid_rows if row["group"] == group]
        summaries[group] = {
            "n": len(group_rows),
            "pre_culture_mean": mean(to_number(row["pre_culture"]) for row in group_rows),
            "post_culture_mean": mean(to_number(row["post_culture"]) for row in group_rows),
            "culture_gain_mean": mean(to_number(row["culture_gain"]) for row in group_rows),
            "culture_gain_sd": sample_sd(to_number(row["culture_gain"]) for row in group_rows),
            "open_post_mean": mean(to_number(row["post_open_score_0_3"]) for row in group_rows),
            "task_correct_rate": percent(sum(int(row["task_correct_0_1"]) for row in group_rows), len(group_rows)),
            "completion_mean_sec": mean(to_number(row["completion_sec"]) for row in group_rows),
            "completion_median_sec": median(to_number(row["completion_sec"]) for row in group_rows),
            "help_mean": mean(to_number(row["help_count"]) for row in group_rows),
            "relevance_mean": mean(to_number(row["relevance_1_5_or_NA"]) for row in group_rows),
            "cultural_clarity_mean": mean(to_number(row["cultural_clarity_1_5_or_NA"]) for row in group_rows),
            "language_accessibility_mean": mean(to_number(row["language_accessibility_1_5_or_NA"]) for row in group_rows),
            "usability_mean": mean(to_number(row["usability_1_5_or_NA"]) for row in group_rows),
            "trust_mean": mean(to_number(row["trust_1_5_or_NA"]) for row in group_rows),
            "reuse_intent_mean": mean(to_number(row["reuse_intent_1_5_or_NA"]) for row in group_rows),
        }

    z_gain = [float(row["culture_gain"]) for row in valid_rows if row["group"] == "智语桥组"]
    c_gain = [float(row["culture_gain"]) for row in valid_rows if row["group"] == "常规检索组"]
    pooled_variance = (
        ((len(z_gain) - 1) * statistics.variance(z_gain) + (len(c_gain) - 1) * statistics.variance(c_gain))
        / (len(z_gain) + len(c_gain) - 2)
    ) if len(z_gain) >= 2 and len(c_gain) >= 2 else 0
    cohen_d = (statistics.fmean(z_gain) - statistics.fmean(c_gain)) / math.sqrt(pooled_variance) if pooled_variance else None
    summary = {
        "received": len(rows),
        "valid": len(valid_rows),
        "future_dated": sum(row["future_date_flag"] for row in rows),
        "source_id_unique": len({row["source_questionnaire_id"] for row in rows}) == len(rows),
        "groups": summaries,
        "between_group": {
            "culture_gain_difference": round(statistics.fmean(z_gain) - statistics.fmean(c_gain), 3),
            "culture_gain_cohen_d": round(cohen_d, 3) if cohen_d is not None else None,
            "interpretation_boundary": "Small non-random sample; report descriptive comparison and effect size without causal generalisation.",
        },
    }
    return rows, summary


LEARNER_THEME_RULES = {
    "快速口语与追问": ("说话很快", "反问", "听不懂", "语速"),
    "本地词语与方言": ("上海话", "侬好", "菜名", "老字号", "方言", "称谓"),
    "文化背景与历史语境": ("背景", "来历", "历史", "语境", "讲究"),
    "来源可信与核验": ("来源", "核实", "不放心", "可靠", "错的信息", "翻错"),
    "多模态与母语脚手架": ("图片", "拼音", "地图", "母语", "语音"),
    "真实任务与城市行走": ("对话", "城市行走", "点单", "真实", "边走边学"),
}

TEACHER_THEME_RULES = {
    "分级与难度适配": ("分级", "难度", "改写", "HSK"),
    "来源追溯": ("来源", "溯源", "核实", "可靠"),
    "教师审核控制": ("审核", "预审", "教师控制", "先经教师"),
    "史实与刻板印象风险": ("史实", "刻板", "错误", "教学事故"),
    "备课效率": ("耗时", "备课", "省一半", "一个多小时"),
    "课堂任务可用性": ("课堂", "活动", "任务", "直接改"),
}


def extract_label(text: str, label: str) -> str:
    match = re.search(rf"(?m)^{re.escape(label)}：([^\r\n]*)", text)
    return match.group(1).strip() if match else ""


def parse_interviews() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    theme_counter: Counter[str] = Counter()
    future_count = 0
    for path in sorted(INTERVIEW_DIR.glob("REAL-*.md"), key=natural_key):
        text = read_text(path)
        interview_id = extract_label(text, "受访者编号") or path.stem
        interview_type = "教师" if interview_id.startswith("REAL-T-") else "学习者"
        date_text = extract_label(text, "访谈日期")
        interview_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        rules = TEACHER_THEME_RULES if interview_type == "教师" else LEARNER_THEME_RULES
        matched_themes = [theme for theme, keywords in rules.items() if any(keyword in text for keyword in keywords)]
        theme_counter.update(matched_themes)
        future_flag = int(interview_date > ANALYSIS_DATE)
        future_count += future_flag
        row = {
            "interview_id": interview_id,
            "interview_type": interview_type,
            "interview_date": date_text,
            "future_date_flag": future_flag,
            "method": extract_label(text, "访谈方式"),
            "duration_min": re.sub(r"[^0-9]", "", extract_label(text, "实际用时")),
            "adult_confirmed": extract_label(text, "受访者已满18周岁"),
            "voluntary_consent": extract_label(text, "自愿参加访谈"),
            "anonymous_quote_consent": extract_label(text, "允许匿名引用回答"),
            "recording_consent": extract_label(text, "允许录音"),
            "themes": "；".join(matched_themes),
            "representative_quote": extract_label(text, "可匿名引用的代表性原话"),
        }
        if interview_type == "学习者":
            row.update({
                "primary_need": extract_label(text, "最需要的功能"),
                "primary_risk": extract_label(text, "对AI回答的主要担忧"),
            })
        else:
            row.update({
                "primary_need": extract_label(text, "教师最突出的备课需求"),
                "primary_risk": extract_label(text, "最高风险内容"),
            })
        rows.append(row)

    valid_rows = [
        row for row in rows
        if row["adult_confirmed"] == "是"
        and row["voluntary_consent"] == "同意"
        and row["anonymous_quote_consent"] == "同意"
    ]
    summary = {
        "received": len(rows),
        "valid": len(valid_rows),
        "learner_count": sum(row["interview_type"] == "学习者" for row in valid_rows),
        "teacher_count": sum(row["interview_type"] == "教师" for row in valid_rows),
        "future_dated": future_count,
        "theme_frequency": counter_rows(theme_counter, len(valid_rows)),
        "recording_consent_count": sum(row["recording_consent"] == "同意" for row in valid_rows),
    }
    return rows, summary


def image_inventory() -> dict[str, Any]:
    extensions = {".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov", ".avi", ".mkv"}
    files = [path for path in RAW_ROOT.rglob("*") if path.is_file() and path.suffix.lower() in extensions]
    return {
        "count": len(files),
        "images": sum(path.suffix.lower() in {".jpg", ".jpeg", ".png", ".heic"} for path in files),
        "videos": sum(path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv"} for path in files),
        "files": [str(path.relative_to(RAW_ROOT)) for path in files],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    q = summary["questionnaires"]
    t = summary["tasks"]
    i = summary["interviews"]
    z = t["groups"]["智语桥组"]
    c = t["groups"]["常规检索组"]
    top_scenes = "、".join(item["item"] for item in q["preferences"]["scenes"][:5])
    top_supports = "、".join(item["item"] for item in q["preferences"]["supports"][:5])
    lines = [
        "# 智语桥真实调研数据审计与分析摘要",
        "",
        f"分析基准日：{summary['analysis_date']}。除经数据提供者确认的统一日期校正外，原始答案内容未改动；公开输出已去除观察者和复核人员姓名。",
        "",
        "## 一、数据完整性",
        "",
        f"- 问卷：收到{q['received']}份，有效{q['valid']}份；实际试用者{q['trial_count']}份。",
        f"- 访谈：收到{i['received']}份，其中学习者{i['learner_count']}份、教师{i['teacher_count']}份。",
        f"- 任务测试：收到{t['received']}份，智语桥组与常规检索组各{z['n']}份。",
        f"- 影像：{summary['media']['images']}张图片、{summary['media']['videos']}段视频。",
        f"- 完全重复问卷：{q['exact_duplicate_records']}份，涉及{q['exact_duplicate_groups']}个重复组。",
        "",
        "## 二、真实性与时点校验",
        "",
        f"- 访谈中有{i['future_dated']}份日期晚于分析基准日。",
        f"- 任务测试中有{t['future_dated']}份日期晚于分析基准日。",
        f"- 日期校正：{summary['date_correction_note']}",
        f"- 当前结论状态：**{summary['evidence_status']}**。问卷、访谈与任务测试可进入正式分析；影像证据暂不纳入。",
        "",
        "## 三、问卷描述性结果",
        "",
        f"- 最受关注场景：{top_scenes}。",
        f"- 最需要的支持：{top_supports}。",
        f"- 实际试用率：{q['trial_rate']:.1%}。",
        f"- 文化判断题正确率：Q30为{q['knowledge_checks']['q30_rate']:.1%}，Q31为{q['knowledge_checks']['q31_rate']:.1%}。",
        "",
        "## 四、任务测试描述性结果",
        "",
        f"- 智语桥组文化增量均值：{z['culture_gain_mean']}；常规检索组：{c['culture_gain_mean']}；组间差：{t['between_group']['culture_gain_difference']}。",
        f"- 智语桥组任务正确率：{z['task_correct_rate']:.1%}；常规检索组：{c['task_correct_rate']:.1%}。",
        f"- 智语桥组完成时长均值：{z['completion_mean_sec']}秒；常规检索组：{c['completion_mean_sec']}秒。",
        f"- 增量效应量（Cohen's d）：{t['between_group']['culture_gain_cohen_d']}。样本非随机，只作描述性比较，不作因果外推。",
        "",
        "## 五、访谈主题",
        "",
    ]
    lines.extend(f"- {item['item']}：{item['count']}/{i['valid']}" for item in i["theme_frequency"])
    lines.extend([
        "",
        "## 六、当前不能代替真人补齐的证据",
        "",
        "- 放入经授权的真实照片与视频，并建立文件名、日期、地点和授权对应表。",
        "- 由立项单位填写推荐意见并盖章；现有通知未要求指导教师签字。",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    if not RAW_ROOT.exists():
        raise SystemExit(f"Raw research folder not found: {RAW_ROOT}")
    questionnaire_rows, questionnaire_summary = parse_questionnaires()
    valid_questionnaire_ids = {row["record_id"] for row in questionnaire_rows if row["valid_record"] == 1}
    task_rows, task_summary = parse_tasks(valid_questionnaire_ids)
    interview_rows, interview_summary = parse_interviews()
    media_summary = image_inventory()

    if task_summary["future_dated"] or interview_summary["future_dated"]:
        evidence_status = "DATE_VERIFICATION_REQUIRED"
    elif media_summary["count"] == 0:
        evidence_status = "ANALYSIS_READY_MEDIA_PENDING"
    else:
        evidence_status = "READY_FOR_FORMAL_REPORTING"
    summary = {
        "analysis_date": ANALYSIS_DATE.isoformat(),
        "date_correction_note": DATE_CORRECTION_NOTE,
        "source_folder": str(RAW_ROOT.relative_to(PROJECT)),
        "evidence_status": evidence_status,
        "questionnaires": questionnaire_summary,
        "tasks": task_summary,
        "interviews": interview_summary,
        "media": media_summary,
    }

    write_csv(ANON_DIR / "智语桥_真实问卷匿名化.csv", questionnaire_rows)
    questionnaire_multi_rows = [
        {"record_id": row["record_id"], "question": f"Q{number}", "item": item}
        for row in questionnaire_rows
        if row["valid_record"] == 1
        for number in (17, 18, 20)
        for item in split_multi(row[f"q{number}"])
    ]
    write_csv(
        ANON_DIR / "智语桥_真实问卷多选长表.csv",
        questionnaire_multi_rows,
        ["record_id", "question", "item"],
    )
    write_csv(ANON_DIR / "智语桥_真实任务测试匿名化.csv", task_rows)
    write_csv(ANON_DIR / "智语桥_真实访谈主题编码.csv", interview_rows)
    interview_theme_rows = [
        {"interview_id": row["interview_id"], "interview_type": row["interview_type"], "theme": theme}
        for row in interview_rows
        if not row["future_date_flag"]
        for theme in split_multi(row["themes"])
    ]
    write_csv(
        ANON_DIR / "智语桥_真实访谈主题长表.csv",
        interview_theme_rows,
        ["interview_id", "interview_type", "theme"],
    )
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    (ANALYSIS_DIR / "智语桥_真实数据分析摘要.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ANALYSIS_DIR / "智语桥_真实数据审计与分析摘要.md").write_text(render_markdown(summary), encoding="utf-8")

    print(json.dumps({
        "evidence_status": evidence_status,
        "questionnaires": questionnaire_summary["received"],
        "valid_questionnaires": questionnaire_summary["valid"],
        "interviews": interview_summary["received"],
        "tasks": task_summary["received"],
        "future_interviews": interview_summary["future_dated"],
        "future_tasks": task_summary["future_dated"],
        "media": media_summary["count"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
