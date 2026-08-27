from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = PROJECT_ROOT / "database"


def _csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return max(0, sum(1 for _ in csv.reader(handle)) - 1)


def _nonempty_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return sum(1 for line in handle if line.strip())


@lru_cache(maxsize=1)
def get_knowledge_stats() -> dict[str, int | str]:
    """Count the records the current retriever can actually load, without initializing models."""
    counts = {
        "hsk_vocabulary": _csv_rows(DATABASE_DIR / "HSK3.0" / "hsk30-master" / "hsk30.csv"),
        "hsk_characters": _csv_rows(DATABASE_DIR / "HSK3.0" / "hsk30-master" / "hsk30-chars.csv"),
        "hsk_grammar": _csv_rows(DATABASE_DIR / "HSK3.0" / "hsk30-master" / "hsk30-grammar.csv"),
        "mucgec_guidelines": _nonempty_lines(DATABASE_DIR / "MUCGEC" / "guidelines" / "guidelines.jsonl"),
        "mucgec_examples": min(200, _nonempty_lines(DATABASE_DIR / "MUCGEC" / "MuCGEC" / "MuCGEC_dev.txt")),
        "teacher_standards": sum(_nonempty_lines(path) for path in (DATABASE_DIR / "teacher_development_standards").glob("*.jsonl")),
        "learning_strategies": _nonempty_lines(DATABASE_DIR / "strategies for learning Chinese" / "chinese_teaching_strategies.jsonl"),
        "research_references": sum(_nonempty_lines(path) for path in (DATABASE_DIR / "references").rglob("*.jsonl")),
        "software_guides": sum(_nonempty_lines(path) for path in (DATABASE_DIR / "softwares").glob("*.jsonl")),
        "haipai_culture": sum(_nonempty_lines(path) for path in (DATABASE_DIR / "haipai_culture").glob("*.jsonl")) if (DATABASE_DIR / "haipai_culture").exists() else 0,
    }
    total = sum(int(value) for value in counts.values())
    return {**counts, "total": total, "total_display": f"{total:,}"}
