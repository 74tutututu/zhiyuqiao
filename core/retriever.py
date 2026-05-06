"""
Knowledge Base Retriever for ZhiYuQiao.

Loads structured knowledge from database/ at startup, routes queries
to the correct domain(s), and returns relevant context for the LLM.
"""

import json
import logging
import random
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

DATABASE_DIR = Path(__file__).resolve().parent.parent / "database"

# ── 常量 ──────────────────────────────────────────────────────────────
MAX_CONTEXT_CHARS = 3000
TFIDF_TOP_K = 5
TFIDF_MIN_SCORE = 0.005
HSK_SAMPLE_SIZE = 20
MUCGEC_EXAMPLE_CAP = 200

# ── 域路由关键词配置 ─────────────────────────────────────────────────
# primary: 高置信度（3分）  secondary: 低置信度（1分）  languages: 语种名（5分）
DOMAIN_KEYWORDS = {
    "hsk": {
        "primary": [
            "HSK", "hsk", "汉语水平考试", "词汇表", "字表", "词表",
            "大纲", "汉语等级", "级别", "几级的词", "哪个等级",
        ],
        "secondary": [
            "词汇", "汉字", "生词", "单词", "拼音", "声调",
            "笔画", "偏旁", "部首", "考试", "备考", "词汇量",
            "字词", "词语", "语法点", "句型",
            "先学哪些词", "初级词汇", "必学词",
        ],
    },
    "mucgec": {
        "primary": [
            "语法纠错", "纠错", "GEC", "MuCGEC", "批改", "改错",
            "病句", "帮我改", "帮我纠正", "纠正句子", "帮我纠错",
        ],
        "secondary": [
            "偏误", "语法错误", "作文批改", "写作纠正", "改正",
            "错误分析", "哪里不对", "有没有错", "是否正确",
            "标点错误", "标点符号", "赘余", "杂糅", "语序",
            "纠正", "错句", "句子错误",
        ],
    },
    "teacher": {
        "primary": [
            "教师标准", "教师能力", "教师素养", "数字素养", "ICT",
            "虚拟教研室", "教研共同体", "UNESCO", "DigCompEdu",
        ],
        "secondary": [
            "教师", "师资", "教研", "教师培训", "教师发展",
            "教师资格", "国际中文教师", "对外汉语教师",
            "教师认证", "考证",
        ],
    },
    "strategies": {
        "primary": [
            "母语负迁移", "对比教学", "国别化教学", "偏误分析",
            "对比语言学", "学习难点", "发音难点",
        ],
        "secondary": [
            "教学策略", "母语", "国别", "难点",
            "不同国家", "各国", "外国学生", "留学生难点",
            "声调难", "声调教学",
        ],
        "languages": [
            "英语", "西班牙语", "法语", "俄语", "德语",
            "葡萄牙语", "印地语", "日语", "韩语", "越南语",
            "阿拉伯语", "泰语",
            "English", "Spanish", "French", "Russian", "German",
            "Portuguese", "Hindi", "Japanese", "Korean",
            "Vietnamese", "Arabic", "Thai",
        ],
        # 国名 -> 对应语种的映射，用于从"泰国学生"推断"泰语"
        "country_to_lang": {
            "泰国": "泰语", "日本": "日语", "韩国": "韩语",
            "越南": "越南语", "印度": "印地语", "法国": "法语",
            "德国": "德语", "俄罗斯": "俄语", "西班牙": "西班牙语",
            "葡萄牙": "葡萄牙语", "巴西": "葡萄牙语",
            "英国": "英语", "美国": "英语", "澳大利亚": "英语",
            "阿拉伯": "阿拉伯语", "中东": "阿拉伯语",
            "沙特": "阿拉伯语", "埃及": "阿拉伯语",
        },
    },
    "references": {
        "primary": [
            "教育智能体", "教育技术", "EdTech", "ChatGPT",
            "大模型", "LLM", "多智能体", "智慧教育",
        ],
        "secondary": [
            "AI", "人工智能", "文献", "研究", "论文", "Agent",
            "智能体", "数智",
        ],
    },
    "softwares": {
        "primary": [
            "Moodle", "moodle", "BigBlueButton", "BBB", "bbb",
            "Jitsi", "jitsi", "LearningApps", "learningapps", "LMS",
        ],
        "secondary": [
            "学习管理系统", "虚拟教室", "视频会议", "教育软件",
            "教学平台", "在线教学工具", "教学工具", "开源软件",
            "数字化工具", "搭建", "部署", "在线课堂", "虚拟课堂",
            "直播教学", "互动模板",
        ],
    },
}


# ── 知识库单例 ───────────────────────────────────────────────────────
class KnowledgeBase:
    """单例：启动时加载全部知识域数据并构建索引。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    # ── 初始化 ────────────────────────────────────────────────────
    def initialize(self):
        if self._initialized:
            return
        logger.info("正在从 %s 加载知识库...", DATABASE_DIR)
        self._load_hsk_data()
        self._load_text_domains()
        self._build_tfidf_indices()
        self._initialized = True
        logger.info(
            "知识库就绪 — HSK(%d词汇, %d汉字, %d语法) "
            "MUCGEC(%d规范, %d示例) 教师(%d) 策略(%d) 文献(%d) 软件(%d)",
            len(self.hsk_vocab), len(self.hsk_chars), len(self.hsk_grammar),
            len(self.mucgec_guidelines), len(self.mucgec_examples),
            len(self.teacher_docs), len(self.strategies),
            len(self.references), len(self.software_docs),
        )

    # ── HSK CSV ───────────────────────────────────────────────────
    def _load_hsk_data(self):
        hsk_dir = DATABASE_DIR / "HSK3.0" / "hsk30-master"
        self.hsk_vocab = pd.read_csv(hsk_dir / "hsk30.csv", encoding="utf-8")
        self.hsk_chars = pd.read_csv(hsk_dir / "hsk30-chars.csv", encoding="utf-8")
        self.hsk_grammar = pd.read_csv(hsk_dir / "hsk30-grammar.csv", encoding="utf-8")

    # ── JSONL 读取 ────────────────────────────────────────────────
    @staticmethod
    def _load_jsonl(filepath):
        docs = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        docs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return docs

    # ── 文本域加载 ────────────────────────────────────────────────
    def _load_text_domains(self):
        # MUCGEC 纠错规范
        self.mucgec_guidelines = self._load_jsonl(
            DATABASE_DIR / "MUCGEC" / "guidelines" / "guidelines.jsonl"
        )

        # MUCGEC 纠错示例
        self.mucgec_examples = []
        dev_path = DATABASE_DIR / "MUCGEC" / "MuCGEC" / "MuCGEC_dev.txt"
        with open(dev_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= MUCGEC_EXAMPLE_CAP:
                    break
                parts = line.strip().split("\t")
                if len(parts) >= 3:
                    self.mucgec_examples.append({
                        "id": parts[0],
                        "original": parts[1],
                        "corrections": parts[2:],
                    })

        # 教师发展标准
        self.teacher_docs = []
        teacher_dir = DATABASE_DIR / "teacher_development_standards"
        for fp in teacher_dir.glob("*.jsonl"):
            self.teacher_docs.extend(self._load_jsonl(fp))

        # 教学策略
        self.strategies = self._load_jsonl(
            DATABASE_DIR / "strategies for learning Chinese"
            / "chinese_teaching_strategies.jsonl"
        )

        # 参考文献（递归）
        self.references = []
        ref_dir = DATABASE_DIR / "references"
        for fp in ref_dir.rglob("*.jsonl"):
            self.references.extend(self._load_jsonl(fp))

        # 教育软件
        self.software_docs = []
        sw_dir = DATABASE_DIR / "softwares"
        for fp in sw_dir.glob("*.jsonl"):
            self.software_docs.extend(self._load_jsonl(fp))

    # ── TF-IDF 索引 ──────────────────────────────────────────────
    def _build_tfidf_indices(self):
        self.tfidf_indices = {}
        domain_data = {
            "mucgec": self.mucgec_guidelines,
            "teacher": self.teacher_docs,
            "references": self.references,
            "softwares": self.software_docs,
            "strategies": self.strategies,
        }
        for name, docs in domain_data.items():
            if not docs:
                continue
            texts = [
                (d.get("title", "") + " " + d.get("content", "")).strip()
                for d in docs
            ]
            vectorizer = TfidfVectorizer(
                analyzer="char",
                ngram_range=(1, 3),
                max_features=15000,
                sublinear_tf=True,
            )
            matrix = vectorizer.fit_transform(texts)
            self.tfidf_indices[name] = (vectorizer, matrix, docs)


# ── 路由函数 ─────────────────────────────────────────────────────────
def _route_query(query):
    """对查询评分，返回得分最高的 1-2 个知识域。"""
    scores = {}
    query_lower = query.lower()

    for domain, kw_config in DOMAIN_KEYWORDS.items():
        score = 0
        for kw in kw_config.get("primary", []):
            if kw.lower() in query_lower:
                score += 3
        for kw in kw_config.get("secondary", []):
            if kw.lower() in query_lower:
                score += 1
        for kw in kw_config.get("languages", []):
            if kw.lower() in query_lower:
                score += 5
        # 国名 -> 语种推断（仅 strategies 域有此配置）
        for country in kw_config.get("country_to_lang", {}):
            if country in query:
                score += 5
        if score > 0:
            scores[domain] = score

    if not scores:
        return ["teacher", "references"]

    sorted_domains = sorted(scores, key=scores.get, reverse=True)
    result = [sorted_domains[0]]
    if len(sorted_domains) > 1:
        if scores[sorted_domains[1]] >= scores[sorted_domains[0]] * 0.5:
            result.append(sorted_domains[1])
    return result


# ── HSK 辅助函数 ─────────────────────────────────────────────────────
def _parse_hsk_level(hsk_level_str):
    """'HSK 3' -> '3', '不限' -> None. 返回字符串以匹配 CSV 列类型。"""
    if not hsk_level_str or hsk_level_str == "不限":
        return None
    m = re.search(r"(\d+)", hsk_level_str)
    return m.group(1) if m else None


def _extract_chinese_tokens(text):
    return re.findall(r"[\u4e00-\u9fff]+", text)


def _search_hsk_vocab(kb, query, level_str):
    df = kb.hsk_vocab
    if level_str:
        if int(level_str) >= 7:
            filtered = df[df["Level"].astype(str).str.startswith("7")]
        else:
            filtered = df[df["Level"] == level_str]
        if filtered.empty:
            return ""
        sample = filtered.head(HSK_SAMPLE_SIZE)
        lines = [f"HSK {level_str}级词汇示例（共{len(filtered)}个词）："]
        for _, row in sample.iterrows():
            lines.append(f"  {row['Simplified']} ({row['Pinyin']}) [{row['POS']}]")
        if len(filtered) > HSK_SAMPLE_SIZE:
            lines.append(f"  ...（还有{len(filtered) - HSK_SAMPLE_SIZE}个词）")
        return "\n".join(lines)

    # 未指定等级时，提供整体统计摘要
    level_counts = df["Level"].value_counts().sort_index()
    lines = [f"HSK词汇库共{len(df)}个词，各等级分布："]
    for lvl, cnt in level_counts.items():
        lines.append(f"  HSK {lvl}级: {cnt}个词")
    return "\n".join(lines)


def _search_hsk_grammar(kb, query, level_num):
    df = kb.hsk_grammar
    if level_num:
        filtered = df[df["Level"] == level_num]
    else:
        filtered = df

    chinese_tokens = _extract_chinese_tokens(query)
    if chinese_tokens:
        mask = pd.Series(False, index=filtered.index)
        for token in chinese_tokens:
            content_col = filtered["Content"].astype(str)
            details_col = filtered["Details"].astype(str)
            mask = mask | content_col.str.contains(token, na=False)
            mask = mask | details_col.str.contains(token, na=False)
        matches = filtered[mask]
        if not matches.empty:
            filtered = matches

    if filtered.empty:
        return ""

    lines = [f"语法点（共{len(filtered)}项）："]
    for _, row in filtered.head(10).iterrows():
        lines.append(f"  [{row['Category']}/{row['Details']}] {row['Content']}")
    return "\n".join(lines)


def _search_hsk_chars(kb, query, level_num):
    df = kb.hsk_chars
    if level_num:
        filtered = df[df["Level"] == level_num]
    else:
        filtered = df

    chinese_tokens = _extract_chinese_tokens(query)
    if chinese_tokens:
        mask = pd.Series(False, index=filtered.index)
        for token in chinese_tokens:
            mask = mask | filtered["Hanzi"].astype(str).str.contains(token, na=False)
        matches = filtered[mask]
        if not matches.empty:
            filtered = matches

    if filtered.empty:
        return ""

    lines = [f"汉字信息（共{len(filtered)}项）："]
    for _, row in filtered.head(10).iterrows():
        lines.append(
            f"  {row['Hanzi']} (Level {row['Level']}, "
            f"书写级别 {row['WritingLevel']}) 例词: {row['Examples']}"
        )
    return "\n".join(lines)


def _lookup_hsk_words(kb, chinese_tokens):
    """在HSK词汇表中查找用户提到的具体中文词。"""
    if not chinese_tokens:
        return ""
    # 将所有中文片段拼合，然后生成2-4字的子串用于匹配
    full_text = "".join(chinese_tokens)
    candidates = set()
    for length in (4, 3, 2):
        for i in range(len(full_text) - length + 1):
            candidates.add(full_text[i:i + length])

    if not candidates:
        return ""

    results = []
    seen = set()
    simplified = kb.hsk_vocab["Simplified"].astype(str)
    for candidate in sorted(candidates, key=len, reverse=True):
        # 词汇表的Simplified列中精确包含候选词
        mask = simplified.str.contains(
            rf"(?:^|\|){re.escape(candidate)}(?:\||$)", na=False, regex=True
        )
        for _, row in kb.hsk_vocab[mask].head(2).iterrows():
            word = row["Simplified"]
            if word not in seen:
                seen.add(word)
                results.append(
                    f"  {word} ({row['Pinyin']}) "
                    f"[HSK {row['Level']}级, {row['POS']}]"
                )
        if len(results) >= 8:
            break

    if results:
        return "词汇查询结果：\n" + "\n".join(results)
    return ""


def _search_hsk(kb, query, hsk_level):
    level_num = _parse_hsk_level(hsk_level)
    is_grammar = any(kw in query for kw in [
        "语法", "句型", "句式", "词类", "grammar",
        "语法点", "句法",
    ])
    is_char = any(kw in query for kw in [
        "汉字", "笔画", "偏旁", "部首", "认读", "书写",
        "字表",
    ])
    is_exam_strategy = any(kw in query for kw in [
        "备考", "策略", "技巧", "方法", "怎么准备",
        "阅读理解", "听力", "写作", "口语考试",
    ])

    parts = []
    if is_grammar:
        parts.append(_search_hsk_grammar(kb, query, level_num))
    if is_char:
        parts.append(_search_hsk_chars(kb, query, level_num))

    if is_exam_strategy:
        # 备考策略类：提供等级概览 + 语法摘要，而非纯词汇列表
        if level_num:
            df = kb.hsk_vocab
            if int(level_num) >= 7:
                filtered = df[df["Level"].astype(str).str.startswith("7")]
            else:
                filtered = df[df["Level"] == level_num]
            vocab_count = len(filtered)

            gram = kb.hsk_grammar
            if level_num:
                gram_filtered = gram[gram["Level"] == level_num]
            else:
                gram_filtered = gram
            grammar_count = len(gram_filtered)

            chars = kb.hsk_chars
            if level_num:
                chars_filtered = chars[chars["Level"] == level_num]
            else:
                chars_filtered = chars
            char_count = len(chars_filtered)

            overview = (
                f"HSK {level_num}级考试范围概览：\n"
                f"  词汇量: {vocab_count}个词\n"
                f"  汉字量: {char_count}个字\n"
                f"  语法点: {grammar_count}项"
            )
            parts.append(overview)

            # 附带该等级的核心语法点（最多8条）
            if not gram_filtered.empty:
                gram_lines = [f"HSK {level_num}级核心语法点："]
                for _, row in gram_filtered.head(8).iterrows():
                    gram_lines.append(
                        f"  [{row['Category']}/{row['Details']}] {row['Content']}"
                    )
                if len(gram_filtered) > 8:
                    gram_lines.append(f"  ...（还有{len(gram_filtered)-8}项语法点）")
                parts.append("\n".join(gram_lines))
        else:
            parts.append(_search_hsk_vocab(kb, query, level_num))
    elif not is_grammar and not is_char:
        parts.append(_search_hsk_vocab(kb, query, level_num))

    chinese_tokens = _extract_chinese_tokens(query)
    word_lookups = _lookup_hsk_words(kb, chinese_tokens)
    if word_lookups:
        parts.append(word_lookups)

    return "\n".join(p for p in parts if p)


# ── TF-IDF 搜索 ─────────────────────────────────────────────────────
def _search_tfidf(kb, domain, query, top_k=TFIDF_TOP_K):
    if domain not in kb.tfidf_indices:
        return ""

    vectorizer, matrix, docs = kb.tfidf_indices[domain]
    query_vec = vectorizer.transform([query])
    scores = cosine_similarity(query_vec, matrix).flatten()
    top_idx = scores.argsort()[-top_k:][::-1]

    results = []
    for idx in top_idx:
        if scores[idx] < TFIDF_MIN_SCORE:
            continue
        doc = docs[idx]
        title = doc.get("title", doc.get("chapter", ""))
        source = doc.get("source", doc.get("tool_name", ""))
        content = doc.get("content", "")
        if len(content) > 800:
            content = content[:800] + "..."
        header = f"【{title}】" if title else ""
        if source:
            header += f"（来源: {source}）"
        results.append(f"{header}\n{content}")

    return "\n---\n".join(results)


# ── 教学策略搜索 ─────────────────────────────────────────────────────
def _resolve_query_languages(query):
    """从查询中提取目标语种，支持直接语种名和国名推断。"""
    query_lower = query.lower()
    matched_langs = set()

    # 直接匹配语种名
    for lang in DOMAIN_KEYWORDS["strategies"]["languages"]:
        if lang.lower() in query_lower:
            matched_langs.add(lang.lower())

    # 国名 -> 语种推断
    for country, lang in DOMAIN_KEYWORDS["strategies"]["country_to_lang"].items():
        if country in query:
            matched_langs.add(lang.lower())

    return matched_langs


def _search_strategies(kb, query):
    matched_langs = _resolve_query_languages(query)

    matches = []
    for entry in kb.strategies:
        title = entry.get("title", "")
        content = entry.get("content", "")
        entry_text = (title + content).lower()

        if matched_langs:
            # 有明确语种时，精确匹配
            for lang in matched_langs:
                if lang in entry_text:
                    text = content if len(content) <= 800 else content[:800] + "..."
                    matches.append(f"【{title}】\n{text}")
                    break
        # 无明确语种时走 TF-IDF 回退（见下方）

    if not matches and not matched_langs:
        # 用 TF-IDF 做语义匹配回退
        tfidf_result = _search_tfidf(kb, "strategies", query)
        if tfidf_result:
            return tfidf_result
        # 最终回退：返回概览
        for entry in kb.strategies[:3]:
            title = entry.get("title", "")
            content = entry.get("content", "")[:600]
            matches.append(f"【{title}】\n{content}")

    return "\n---\n".join(matches[:3])


# ── MUCGEC 搜索 ──────────────────────────────────────────────────────
def _search_mucgec(kb, query):
    parts = []

    guideline_result = _search_tfidf(kb, "mucgec", query)
    if guideline_result:
        parts.append("【纠错规范】\n" + guideline_result)

    if kb.mucgec_examples:
        # 尝试找到与查询相关的示例
        chinese_tokens = _extract_chinese_tokens(query)
        relevant_examples = []
        if chinese_tokens:
            for ex in kb.mucgec_examples:
                for token in chinese_tokens:
                    if token in ex["original"]:
                        relevant_examples.append(ex)
                        break
                if len(relevant_examples) >= 3:
                    break

        # 不足则随机补充
        if len(relevant_examples) < 3:
            remaining = [e for e in kb.mucgec_examples if e not in relevant_examples]
            fill_count = min(3 - len(relevant_examples), len(remaining))
            relevant_examples.extend(random.sample(remaining, fill_count))

        example_lines = ["【纠错示例】"]
        for ex in relevant_examples[:3]:
            corrections_str = " / ".join(ex["corrections"][:2])
            example_lines.append(
                f"  原句: {ex['original']}\n  修改: {corrections_str}"
            )
        parts.append("\n".join(example_lines))

    return "\n\n".join(parts)


# ── 软件搜索 ─────────────────────────────────────────────────────────
def _search_softwares(kb, query):
    """软件域搜索：先 TF-IDF，若无明确工具名则补充各工具概览。"""
    query_lower = query.lower()
    # 检查是否查询特定工具
    tool_names = ["moodle", "bigbluebutton", "bbb", "jitsi", "learningapps"]
    has_specific_tool = any(t in query_lower for t in tool_names)

    tfidf_result = _search_tfidf(kb, "softwares", query)

    if has_specific_tool and tfidf_result:
        return tfidf_result

    # 模糊查询：在 TF-IDF 结果基础上，补充各工具概览
    tool_overviews = []
    seen_tools = set()
    for doc in kb.software_docs:
        tool = doc.get("tool_name", "")
        if tool and tool not in seen_tools:
            seen_tools.add(tool)
            title = doc.get("title", "")
            content = doc.get("content", "")[:200]
            tool_overviews.append(f"【{tool} - {title}】\n{content}")
            if len(tool_overviews) >= 4:
                break

    parts = []
    if tfidf_result:
        parts.append(tfidf_result)
    if tool_overviews and not has_specific_tool:
        parts.append("【可用教学工具概览】\n" + "\n---\n".join(tool_overviews))

    return "\n\n".join(parts)


# ── 公开 API ─────────────────────────────────────────────────────────
_kb = KnowledgeBase()


def get_relevant_info(query_text, hsk_level="不限"):
    """
    检索与用户查询相关的知识库内容，注入到系统提示词中。

    替代旧的 CSV 检索。根据查询路由到合适的知识域，
    返回格式化的上下文字符串。
    """
    # 防御：前端组件可能传入 list 而非 str
    if isinstance(query_text, list):
        query_text = " ".join(str(item) for item in query_text)
    query_text = str(query_text)

    try:
        _kb.initialize()
    except Exception as e:
        logger.error("知识库加载失败: %s", e)
        return "知识库加载失败，将使用通用知识回答。"

    domains = _route_query(query_text)
    logger.info("查询路由到域: %s", domains)

    results = []
    for domain in domains:
        try:
            if domain == "hsk":
                result = _search_hsk(_kb, query_text, hsk_level)
            elif domain == "strategies":
                result = _search_strategies(_kb, query_text)
            elif domain == "mucgec":
                result = _search_mucgec(_kb, query_text)
            elif domain == "softwares":
                result = _search_softwares(_kb, query_text)
            else:
                result = _search_tfidf(_kb, domain, query_text)

            if result:
                results.append(result)
        except Exception as e:
            logger.warning("域 %s 搜索失败: %s", domain, e)

    if results:
        combined = "\n\n".join(results)
        if len(combined) > MAX_CONTEXT_CHARS:
            combined = combined[:MAX_CONTEXT_CHARS] + "\n...（更多内容已截断）"
        return combined

    return "未在知识库中找到直接相关内容，请根据专业知识回答。"


def get_relevant_info_by_domains(query_text, domains, hsk_level="不限"):
    """
    根据指定域返回知识库上下文。

    domains: 可迭代的域名称列表，如 ["hsk", "softwares"]。
    """
    if isinstance(query_text, list):
        query_text = " ".join(str(item) for item in query_text)
    query_text = str(query_text)
    domains = [str(d).strip() for d in (domains or []) if str(d).strip()]

    if not domains:
        return get_relevant_info(query_text, hsk_level=hsk_level)

    try:
        _kb.initialize()
    except Exception as e:
        logger.error("知识库加载失败: %s", e)
        return "知识库加载失败，将使用通用知识回答。"

    results = []
    for domain in domains:
        try:
            if domain == "hsk":
                result = _search_hsk(_kb, query_text, hsk_level)
            elif domain == "strategies":
                result = _search_strategies(_kb, query_text)
            elif domain == "mucgec":
                result = _search_mucgec(_kb, query_text)
            elif domain == "softwares":
                result = _search_softwares(_kb, query_text)
            else:
                result = _search_tfidf(_kb, domain, query_text)

            if result:
                results.append(result)
        except Exception as e:
            logger.warning("域 %s 搜索失败: %s", domain, e)

    if results:
        combined = "\n\n".join(results)
        if len(combined) > MAX_CONTEXT_CHARS:
            combined = combined[:MAX_CONTEXT_CHARS] + "\n...（更多内容已截断）"
        return combined

    return "未在知识库中找到直接相关内容，请根据专业知识回答。"
