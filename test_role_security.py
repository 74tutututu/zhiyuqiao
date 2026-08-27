#!/usr/bin/env python3
"""Role, CSRF, password and authorization regression checks without model calls."""

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

db_file = tempfile.NamedTemporaryFile(prefix="zhiyuqiao_role_", suffix=".sqlite3", delete=False)
db_file.close()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(db_file.name).as_posix()}"

from fastapi.testclient import TestClient

from core.assistant_service import _target_level, list_assistant_skills
from core.account_profiles import AccountProfile
import main as main_module
from main import app


def build_student(level: str) -> AccountProfile:
    return AccountProfile(
        user_id="test",
        username="test_student",
        display_name="测试学习者",
        teaching_languages=("中文",),
        account_role="student",
        teacher_level="experienced_teacher",
        student_level=level,
        learning_goal="culture_explorer",
        theme_name="china_red",
    )


if __name__ == "__main__":
    assert _target_level(build_student("hsk3")) == "HSK3"
    assert _target_level(build_student("hsk4")) == "HSK4"
    assert list_assistant_skills("student")[0]["key"] == "culture_explorer"

    with TestClient(app) as client:
        register_page = client.get("/register")
        assert register_page.status_code == 200
        csrf = client.cookies.get("zhiyuqiao_csrf")
        assert csrf and f'value="{csrf}"' in register_page.text
        assert register_page.headers["x-frame-options"] == "DENY"

        short_password = client.post(
            "/register",
            data={
                "csrf_token": csrf,
                "accept_terms": "yes",
                "username": "short_pwd",
                "display_name": "短密码测试",
                "password": "1234567",
                "account_role": "student",
                "student_level": "hsk3",
                "learning_goal": "culture_explorer",
                "theme_name": "china_red",
                "teaching_languages": "中文",
            },
        )
        assert short_password.status_code == 400
        assert "至少需要8个字符" in short_password.text

        registered = client.post(
            "/register",
            data={
                "csrf_token": csrf,
                "accept_terms": "yes",
                "username": "role_student",
                "display_name": "角色测试学习者",
                "password": "Secure123",
                "account_role": "student",
                "student_level": "hsk3",
                "learning_goal": "culture_explorer",
                "theme_name": "china_red",
                "teaching_languages": ["中文", "English"],
            },
            follow_redirects=False,
        )
        assert registered.status_code == 303
        assert registered.headers["location"] == "/student"

        teacher_page = client.get("/teacher", follow_redirects=False)
        assert teacher_page.status_code == 303
        assert teacher_page.headers["location"] == "/student"

        language_update = client.post(
            "/settings",
            data={
                "csrf_token": csrf,
                "display_name": "角色测试学习者",
                "account_role": "student",
                "student_level": "hsk3",
                "learning_goal": "culture_explorer",
                "theme_name": "china_red",
                "teaching_languages": ["中文", "English"],
                "primary_language": "English",
            },
        )
        assert language_update.status_code == 200
        assert client.get("/api/me").json()["user"]["instruction_language"] == "English"

        denied = client.post(
            "/api/message",
            headers={"X-CSRF-Token": csrf},
            json={"skill_key": "bridge_policy_interpretation", "text": "测试", "history": []},
        )
        assert denied.status_code == 400

        missing_csrf = client.post(
            "/api/message",
            json={"skill_key": "culture_explorer", "text": "测试", "history": []},
        )
        assert missing_csrf.status_code == 403

        original_stream = main_module.run_assistant_turn_stream
        try:
            def fake_stream(**_):
                yield "第一段"
                yield "第一段，第二段。"

            main_module.run_assistant_turn_stream = fake_stream
            streamed = client.post(
                "/api/message/stream",
                headers={"X-CSRF-Token": csrf},
                json={"skill_key": "student_tutor", "text": "测试流式回答", "history": []},
            )
            assert streamed.status_code == 200
            assert streamed.headers["content-type"].startswith("application/x-ndjson")
            assert '"type": "done"' in streamed.text
            assert "第一段，第二段。" in streamed.text
        finally:
            main_module.run_assistant_turn_stream = original_stream

        privacy = client.get("/privacy")
        assert privacy.status_code == 200
        assert "第三方大语言模型" in privacy.text

    print("[OK] role and security regressions passed")
