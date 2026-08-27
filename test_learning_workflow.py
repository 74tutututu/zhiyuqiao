#!/usr/bin/env python3
"""Student task and teacher artifact workflow checks without model calls."""

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

db_file = tempfile.NamedTemporaryFile(prefix="zhiyuqiao_workflow_", suffix=".sqlite3", delete=False)
db_file.close()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(db_file.name).as_posix()}"

from fastapi.testclient import TestClient

from main import app


def register(client: TestClient, *, username: str, display_name: str, role: str) -> str:
    page = client.get("/register")
    csrf = client.cookies.get("zhiyuqiao_csrf")
    assert page.status_code == 200 and csrf
    response = client.post(
        "/register",
        data={
            "csrf_token": csrf,
            "accept_terms": "yes",
            "username": username,
            "display_name": display_name,
            "password": "Secure123",
            "account_role": role,
            "student_level": "hsk2",
            "learning_goal": "culture_explorer",
            "teacher_level": "experienced_teacher",
            "theme_name": "china_red",
            "teaching_languages": "中文",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    return csrf


if __name__ == "__main__":
    with TestClient(app) as student_client:
        student_csrf = register(
            student_client,
            username="workflow_student",
            display_name="闭环测试学习者",
            role="student",
        )
        created = student_client.post(
            "/api/student/tasks",
            headers={"X-CSRF-Token": student_csrf},
            json={
                "topic": "杨浦滨江",
                "title": "杨浦滨江学习任务",
                "prompt": "观察工业遗产并用中文描述。",
                "assistant_reply": "请记录建筑材料和用途变化。",
            },
        )
        assert created.status_code == 200, created.text
        task_id = created.json()["task"]["id"]
        assert created.json()["progress"]["percent"] == 0

        completed = student_client.post(
            f"/api/student/tasks/{task_id}/complete",
            headers={"X-CSRF-Token": student_csrf},
            json={"reflection": "我学会了用‘以前……现在……’描述城市更新。"},
        )
        assert completed.status_code == 200, completed.text
        assert completed.json()["task"]["status"] == "completed"
        assert completed.json()["progress"] == {"completed": 1, "total": 6, "percent": 17}
        task_list = student_client.get("/api/student/tasks")
        assert task_list.status_code == 200
        assert task_list.json()["tasks"][0]["title"] == "杨浦滨江学习任务"

        denied_artifact = student_client.post(
            "/api/teacher/artifacts",
            headers={"X-CSRF-Token": student_csrf},
            json={"title": "越权", "skill_key": "x", "prompt": "测试", "content": "测试"},
        )
        assert denied_artifact.status_code == 403

    with TestClient(app) as teacher_client:
        teacher_csrf = register(
            teacher_client,
            username="workflow_teacher",
            display_name="闭环测试教师",
            role="teacher",
        )
        created = teacher_client.post(
            "/api/teacher/artifacts",
            headers={"X-CSRF-Token": teacher_csrf},
            json={
                "title": "外滩与陆家嘴对比课",
                "skill_key": "haipai_lesson_lab",
                "prompt": "设计一节30分钟对比课。",
                "content": "## 教学目标\n学习者能够用‘以前’和‘现在’完成对比表达。",
            },
        )
        assert created.status_code == 200, created.text
        artifact_id = created.json()["artifact"]["id"]

        page = teacher_client.get(f"/teacher/artifacts/{artifact_id}")
        assert page.status_code == 200
        assert "AI 草稿 · 待审核" in page.text
        updated = teacher_client.post(
            f"/teacher/artifacts/{artifact_id}",
            data={
                "csrf_token": teacher_csrf,
                "title": "外滩与陆家嘴对比课（已核验）",
                "content": "已核验的教案正文。",
                "review_status": "reviewed",
            },
            follow_redirects=False,
        )
        assert updated.status_code == 303
        reviewed = teacher_client.get(f"/teacher/artifacts/{artifact_id}")
        assert "教师已审核" in reviewed.text
        exported = teacher_client.get(f"/teacher/artifacts/{artifact_id}/download")
        assert exported.status_code == 200
        assert "已核验的教案正文" in exported.text

        denied_task = teacher_client.post(
            "/api/student/tasks",
            headers={"X-CSRF-Token": teacher_csrf},
            json={"topic": "测试", "title": "测试", "prompt": "测试", "assistant_reply": "测试"},
        )
        assert denied_task.status_code == 403

    print("[OK] learning workflow regressions passed")
