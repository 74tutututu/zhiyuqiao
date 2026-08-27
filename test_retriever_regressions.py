"""
Regression checks for retriever recall quality.

Run with:
    ./.venv/Scripts/python.exe test_retriever_regressions.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.retriever import get_haipai_source_cards, get_relevant_info


def assert_contains(text: str, needle: str, label: str) -> None:
    if needle.lower() not in text.lower():
        raise AssertionError(f"{label}: expected to contain {needle!r}, got: {text[:300]!r}")


def test_moodle_query() -> None:
    result = get_relevant_info("Moodle怎么用", "不限")
    assert result.strip(), "Moodle query returned empty result"
    assert_contains(result, "moodle", "Moodle query")


def test_hsk_char_query() -> None:
    result = get_relevant_info("以“車”造词", "不限")
    assert result.strip(), "HSK char query returned empty result"
    assert_contains(result, "车", "HSK char query")


def test_mucgec_sentence_query() -> None:
    query = "“因为在冰箱里没什么东西也做很好吃的菜。”是病句吗，怎么修改"
    result = get_relevant_info(query, "不限")
    assert result.strip(), "MuCGEC sentence query returned empty result"
    assert_contains(result, "冰箱", "MuCGEC sentence query")
    assert_contains(result, "改", "MuCGEC sentence query")


def test_haipai_traceable_query() -> None:
    result = get_relevant_info("杨浦滨江工业遗产观察任务", "HSK 3")
    assert_contains(result, "保护利用", "Haipai culture query")
    assert_contains(result, "来源", "Haipai culture source")
    cards = get_haipai_source_cards("杨浦滨江工业遗产")
    assert cards, "Haipai source cards returned empty"
    assert str(cards[0].get("source_url", "")).startswith("https://www.shanghai.gov.cn/")


if __name__ == "__main__":
    test_moodle_query()
    test_hsk_char_query()
    test_mucgec_sentence_query()
    test_haipai_traceable_query()
    print("[OK] retriever regressions passed")
