"""
Configuration management for ZhiYuQiao system.

Centralizes all configurable parameters to make tuning easier.
"""

import os
from pathlib import Path

# ── 项目路径配置 ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = PROJECT_ROOT / "database"
DATA_DIR = PROJECT_ROOT / "data"


def _resolve_vector_db_dir() -> Path:
    configured = os.getenv("ZHIYUQIAO_VECTOR_DB_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()

    project_candidate = DATA_DIR / "vectors"
    # Chroma 的 Windows HNSW 持久化后端在非 ASCII 长路径下可能只写出
    # index_metadata.pickle 而缺失二进制索引。此时使用同盘纯 ASCII 运行目录。
    if os.name == "nt" and (
        any(ord(char) > 127 for char in str(project_candidate))
        or len(str(project_candidate)) > 120
    ):
        return Path(PROJECT_ROOT.anchor) / "zhiyuqiao_runtime" / "vectors"
    return project_candidate


VECTOR_DB_DIR = _resolve_vector_db_dir()

# ── 向量数据库配置 ────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv(
    "ZHIYUQIAO_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
EMBEDDING_BACKEND = os.getenv("ZHIYUQIAO_EMBEDDING_BACKEND", "torch").strip().lower() or "torch"
EMBEDDING_ONNX_FILE = os.getenv("ZHIYUQIAO_EMBEDDING_ONNX_FILE", "").strip()
VECTOR_SEARCH_TOP_K = 5
VECTOR_DB_PATH = str(VECTOR_DB_DIR)

# ── 缓存配置 ──────────────────────────────────────────────────
CACHE_MAX_SIZE = 1000          # 最大缓存条目数
CACHE_TTL_MINUTES = 60         # 缓存 TTL（分钟）

# ── 文本处理配置 ──────────────────────────────────────────────
MAX_CONTEXT_CHARS = 3000       # 最大上下文长度
TFIDF_TOP_K = 5                # TF-IDF 返回条数
TFIDF_MIN_SCORE = 0.005        # TF-IDF 最小得分阈值

# ── 日志配置 ──────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ── API 配置 ──────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TEMPERATURE = 0.3
DEEPSEEK_TIMEOUT_SECONDS = 60

# ── Gradio 配置 ───────────────────────────────────────────────
GRADIO_SERVER_NAME = "0.0.0.0"
GRADIO_SERVER_PORT = 7860
GRADIO_SHARE = False
GRADIO_ALLOWED_PATHS = ["assets"]

# ── HSK 配置 ───────────────────────────────────────────────
HSK_SAMPLE_SIZE = 20
HSK_LEVELS = ["不限", "HSK 1", "HSK 2", "HSK 3", "HSK 4", "HSK 5", "HSK 6"]

# ── MUCGEC 配置 ───────────────────────────────────────────────
MUCGEC_EXAMPLE_CAP = 200  # 最多加载多少个示例

# ── 线程配置 ───────────────────────────────────────────────────
MAX_WORKER_THREADS = 4    # 最大工作线程数


def get_config_dict() -> dict:
    """获取所有配置项作为字典。"""
    return {
        "project_root": str(PROJECT_ROOT),
        "database_dir": str(DATABASE_DIR),
        "vector_db_dir": str(VECTOR_DB_DIR),
        "embedding_model": EMBEDDING_MODEL,
        "embedding_backend": EMBEDDING_BACKEND,
        "embedding_onnx_file": EMBEDDING_ONNX_FILE,
        "vector_search_top_k": VECTOR_SEARCH_TOP_K,
        "cache_max_size": CACHE_MAX_SIZE,
        "cache_ttl_minutes": CACHE_TTL_MINUTES,
        "max_context_chars": MAX_CONTEXT_CHARS,
        "tfidf_top_k": TFIDF_TOP_K,
        "tfidf_min_score": TFIDF_MIN_SCORE,
        "log_level": LOG_LEVEL,
        "deepseek_model": DEEPSEEK_MODEL,
        "deepseek_temperature": DEEPSEEK_TEMPERATURE,
        "gradio_server_port": GRADIO_SERVER_PORT,
        "hsk_sample_size": HSK_SAMPLE_SIZE,
        "mucgec_example_cap": MUCGEC_EXAMPLE_CAP,
        "max_worker_threads": MAX_WORKER_THREADS,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(get_config_dict(), indent=2, ensure_ascii=False))
