#!/usr/bin/env python3
"""FastAPI 最小启动测试，不访问外部模型接口。"""

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

TEMP_DB = Path(tempfile.gettempdir()) / "zhiyuqiao_smoke.sqlite3"
os.environ["DATABASE_URL"] = f"sqlite:///{TEMP_DB.as_posix()}"

from fastapi.testclient import TestClient

from main import app


if __name__ == "__main__":
    with TestClient(app) as client:
        response = client.get("/health")
        response.raise_for_status()
        assert response.json() == {"status": "ok", "service": "zhiyuqiao"}
    print("[OK] FastAPI minimal launch test passed")
