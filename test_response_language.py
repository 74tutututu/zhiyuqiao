"""Language-policy wiring for every student/teacher module and both endpoints."""
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

_temp = tempfile.TemporaryDirectory(prefix="zhiyuqiao_language_")
os.environ["DATABASE_URL"] = "sqlite:///" + (Path(_temp.name) / "test.sqlite3").as_posix()

from fastapi.testclient import TestClient
from core import assistant_service as service
from core.ai_agent import _build_system_prompt
from core.response_language import LANGUAGE_NAMES, reply_language_policy
from test_conversation_routing import fake_profile
import main


def check_policy_and_modules():
    context = SimpleNamespace(learner_level="HSK 2", confidence="high", teaching_goal="test", evidence="test")
    count = 0
    for role in ("student", "teacher"):
        profile = fake_profile(role=role)
        for skill in service.list_assistant_skills(role):
            for language in ("auto", "profile", *LANGUAGE_NAMES):
                kwargs = dict(skill_key=skill["key"], text="hello?", profile=profile, response_language=language)
                with patch.object(service, "generate_response", return_value="hello") as mock:
                    assert service.run_assistant_turn(**kwargs) == "hello"
                    assert mock.call_args.kwargs["response_language"] == language
                    prompt = _build_system_prompt("reference", profile, context,
                                                  mock.call_args.kwargs["system_extension"], language)
                    assert reply_language_policy(language, profile.instruction_language) in prompt
                    assert "不过度困难的中文回答" not in prompt
                with patch.object(service, "generate_response_stream", return_value=iter(["hello"])) as mock:
                    assert list(service.run_assistant_turn_stream(**kwargs)) == ["hello"]
                    assert mock.call_args.kwargs["response_language"] == language
                count += 1
    print(f"[OK] {count} module/language combinations in streaming and non-streaming paths")


def check_http():
    with TestClient(main.app) as client:
        client.get("/register")
        csrf = client.cookies.get("zhiyuqiao_csrf")
        result = client.post("/register", data={
            "csrf_token": csrf, "accept_terms": "yes", "username": "language_test",
            "display_name": "Language Test", "password": "LanguageTest916",
            "account_role": "student", "student_level": "hsk2", "learning_goal": "culture_explorer",
            "theme_name": "china_red", "teaching_languages": "中文",
        })
        assert result.status_code == 200
        page = client.get("/student", headers={"Accept-Language": "en"})
        assert 'id="response-language"' in page.text and 'Match my question' in page.text
        assert "I'd like to start exploring" in page.text or "I&#39;d like to start exploring" in page.text
        headers = {"X-CSRF-Token": csrf}
        for endpoint, name, value in (("/api/message", "run_assistant_turn", "Hello"),
                                       ("/api/message/stream", "run_assistant_turn_stream", ["Hello"])):
            with patch.object(main, name, return_value=value) as mock:
                response = client.post(endpoint, headers=headers, json={
                    "skill_key": "student_tutor", "text": "你好", "response_language": "en"})
                assert response.status_code == 200, response.text
                assert mock.call_args.kwargs["response_language"] == "en"
                response = client.post(endpoint, headers=headers, json={"skill_key": "student_tutor", "text": "hello?"})
                assert response.status_code == 200
                assert mock.call_args.kwargs["response_language"] == "auto"
            invalid = client.post(endpoint, headers=headers, json={
                "skill_key": "student_tutor", "text": "hello", "response_language": "invalid"})
            assert invalid.status_code == 422
    print("[OK] composer, localized shortcuts, request validation and both HTTP endpoints")


if __name__ == "__main__":
    try:
        check_policy_and_modules()
        check_http()
    finally:
        from core.db import engine
        engine.dispose()
        _temp.cleanup()
