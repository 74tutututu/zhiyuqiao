from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from core.account_profiles import (
    ACCOUNT_ROLE_LABELS,
    DEFAULT_THEME,
    LANGUAGE_OPTIONS,
    LEARNING_GOAL_LABELS,
    SESSION_COOKIE_NAME,
    SESSION_TTL_DAYS,
    STUDENT_LEVEL_LABELS,
    TEACHER_LEVEL_LABELS,
    THEME_LABELS,
    authenticate_teacher,
    complete_learning_task,
    count_users,
    create_learning_task,
    create_teacher_artifact,
    create_user_session,
    delete_user_sessions_for_user,
    delete_user_session,
    get_teacher_profile_by_session,
    get_learning_progress,
    get_teacher_artifact,
    initialize_profile_store,
    list_learning_tasks,
    list_teacher_artifacts,
    register_account,
    update_teacher_artifact,
    update_account_profile,
)
from core.assistant_service import list_assistant_skills, run_assistant_turn
from core.content_catalog import get_knowledge_stats
from core.retriever import get_haipai_source_cards
from core.web_security import (
    CSRF_COOKIE_NAME,
    SlidingWindowLimiter,
    client_key,
    ensure_csrf_token,
    secure_cookies_enabled,
    validate_csrf_token,
)

PROJECT_ROOT = Path(__file__).resolve().parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_profile_store()
    yield


app = FastAPI(title="智语桥 ZhiYuQiao", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

LOGIN_LIMITER = SlidingWindowLimiter(limit=6, window_seconds=60)
MESSAGE_LIMITER = SlidingWindowLimiter(limit=30, window_seconds=60)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    token = ensure_csrf_token(request)
    response = await call_next(request)
    if not request.cookies.get(CSRF_COOKIE_NAME):
        response.set_cookie(
            CSRF_COOKIE_NAME,
            token,
            httponly=False,
            samesite="lax",
            secure=secure_cookies_enabled(),
            max_age=SESSION_TTL_DAYS * 24 * 60 * 60,
            path="/",
        )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=(self)")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
    )
    if secure_cookies_enabled():
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class AssistantMessageRequest(BaseModel):
    skill_key: str = Field(default="teacher_advisor", description="当前选择的 skill")
    text: str = Field(..., min_length=1, max_length=6000, description="用户输入")
    history: list[ChatMessage] = Field(default_factory=list, max_length=20, description="当前会话历史")


class LearningTaskCreateRequest(BaseModel):
    topic: str = Field(default="自主探索", max_length=64)
    title: str = Field(default="学习任务", max_length=128)
    prompt: str = Field(..., min_length=1, max_length=6000)
    assistant_reply: str = Field(..., min_length=1, max_length=16000)


class LearningTaskCompleteRequest(BaseModel):
    reflection: str = Field(..., min_length=2, max_length=2000)


class TeacherArtifactCreateRequest(BaseModel):
    title: str = Field(default="教案草稿", max_length=128)
    skill_key: str = Field(default="teacher_advisor", max_length=64)
    prompt: str = Field(..., min_length=1, max_length=6000)
    content: str = Field(..., min_length=1, max_length=30000)


def _theme_choices() -> list[tuple[str, str]]:
    return [(value, key) for key, value in THEME_LABELS.items()]


def _teacher_level_choices() -> list[tuple[str, str]]:
    return [(value, key) for key, value in TEACHER_LEVEL_LABELS.items()]


def _role_choices() -> list[tuple[str, str]]:
    return [(value, key) for key, value in ACCOUNT_ROLE_LABELS.items()]


def _student_level_choices() -> list[tuple[str, str]]:
    return [(value, key) for key, value in STUDENT_LEVEL_LABELS.items()]


def _learning_goal_choices() -> list[tuple[str, str]]:
    return [(value, key) for key, value in LEARNING_GOAL_LABELS.items()]


def _normalize_form_languages(raw: list[str] | None) -> list[str]:
    cleaned = [str(item).strip() for item in raw or [] if str(item).strip()]
    return cleaned or ["中文"]


def _current_user(request: Request, *, touch: bool = True):
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    return get_teacher_profile_by_session(session_id, touch=touch)


def _page_context(request: Request, **kwargs: Any) -> dict[str, Any]:
    context = {
        "request": request,
        "language_options": LANGUAGE_OPTIONS,
        "role_choices": _role_choices(),
        "teacher_level_choices": _teacher_level_choices(),
        "student_level_choices": _student_level_choices(),
        "learning_goal_choices": _learning_goal_choices(),
        "theme_choices": _theme_choices(),
        "default_theme": DEFAULT_THEME,
        "csrf_token": ensure_csrf_token(request),
        "knowledge_stats": get_knowledge_stats(),
        **kwargs,
    }
    return context


def _redirect_with_session(url: str, session_id: str) -> RedirectResponse:
    response = RedirectResponse(url=url, status_code=303)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        httponly=True,
        samesite="lax",
        secure=secure_cookies_enabled(),
        max_age=SESSION_TTL_DAYS * 24 * 60 * 60,
        path="/",
    )
    return response


def _role_home(user) -> str:
    return "/student" if user.account_role == "student" else "/teacher"


def _login_required(request: Request):
    user = _current_user(request)
    if user is None:
        return None, RedirectResponse(url="/login", status_code=303)
    return user, None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = _current_user(request)
    if user is not None:
        return RedirectResponse(url=_role_home(user), status_code=303)
    if count_users() == 0:
        return RedirectResponse(url="/register", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    current = _current_user(request)
    if current is not None:
        return RedirectResponse(url=_role_home(current), status_code=303)

    return templates.TemplateResponse(
        "register.html",
        _page_context(
            request,
            page_title="注册账号",
            first_user=(count_users() == 0),
            error="",
            form_data={},
        ),
    )


@app.post("/register", response_class=HTMLResponse)
async def register_submit(request: Request):
    current = _current_user(request)
    if current is not None:
        return RedirectResponse(url=_role_home(current), status_code=303)

    form = await request.form()
    if not validate_csrf_token(request, form.get("csrf_token")):
        raise HTTPException(status_code=403, detail="页面已过期，请刷新后重试。")
    if str(form.get("accept_terms", "")) != "yes":
        raise HTTPException(status_code=400, detail="请先阅读并同意隐私说明。")
    form_data = {
        "username": str(form.get("username", "")).strip(),
        "display_name": str(form.get("display_name", "")).strip(),
        "account_role": str(form.get("account_role", "teacher")).strip(),
        "teacher_level": str(form.get("teacher_level", "")).strip(),
        "student_level": str(form.get("student_level", "hsk3")).strip(),
        "learning_goal": str(form.get("learning_goal", "culture_explorer")).strip(),
        "theme_name": str(form.get("theme_name", DEFAULT_THEME)).strip(),
    }
    teaching_languages = _normalize_form_languages(form.getlist("teaching_languages"))
    password = str(form.get("password", ""))

    try:
        profile = register_account(
            username=form_data["username"],
            display_name=form_data["display_name"],
            password=password,
            teaching_languages=teaching_languages,
            account_role=form_data["account_role"],
            teacher_level=form_data["teacher_level"],
            student_level=form_data["student_level"],
            learning_goal=form_data["learning_goal"],
            theme_name=form_data["theme_name"],
        )
    except ValueError as exc:
        return templates.TemplateResponse(
            "register.html",
            _page_context(
                request,
                page_title="注册账号",
                first_user=(count_users() == 0),
                error=str(exc),
                form_data={**form_data, "teaching_languages": teaching_languages},
            ),
            status_code=400,
        )

    session_id = create_user_session(profile.user_id)
    return _redirect_with_session(_role_home(profile), session_id)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    current = _current_user(request)
    if current is not None:
        return RedirectResponse(url=_role_home(current), status_code=303)
    if count_users() == 0:
        return RedirectResponse(url="/register", status_code=303)

    return templates.TemplateResponse(
        "login.html",
        _page_context(
            request,
            page_title="登录",
            error="",
            identifier="",
        ),
    )


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request):
    form = await request.form()
    if not validate_csrf_token(request, form.get("csrf_token")):
        raise HTTPException(status_code=403, detail="页面已过期，请刷新后重试。")
    identifier = str(form.get("identifier", "")).strip()
    password = str(form.get("password", ""))

    allowed, retry_after = LOGIN_LIMITER.allow(f"{client_key(request)}:{identifier.casefold()}")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"登录尝试过于频繁，请在 {retry_after} 秒后重试。",
            headers={"Retry-After": str(retry_after)},
        )

    profile = authenticate_teacher(identifier, password)
    if profile is None:
        return templates.TemplateResponse(
            "login.html",
            _page_context(
                request,
                page_title="登录",
                error="账号/账号名或密码错误，请重试。",
                identifier=identifier,
            ),
            status_code=400,
        )

    session_id = create_user_session(profile.user_id)
    return _redirect_with_session(_role_home(profile), session_id)


@app.post("/logout")
async def logout(request: Request):
    form = await request.form()
    if not validate_csrf_token(request, form.get("csrf_token")):
        raise HTTPException(status_code=403, detail="页面已过期，请刷新后重试。")
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    delete_user_session(session_id)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@app.get("/assistant", response_class=HTMLResponse)
async def assistant_page(request: Request):
    user, redirect = _login_required(request)
    if redirect is not None:
        return redirect

    return RedirectResponse(url=_role_home(user), status_code=303)


@app.get("/teacher", response_class=HTMLResponse)
async def teacher_workspace(request: Request):
    user, redirect = _login_required(request)
    if redirect is not None:
        return redirect
    if user.account_role != "teacher":
        return RedirectResponse(url="/student", status_code=303)

    return templates.TemplateResponse(
        "teacher_dashboard.html",
        _page_context(
            request,
            page_title="教师工作台",
            user=user.to_dict(),
            skills=list_assistant_skills("teacher"),
            artifacts=list_teacher_artifacts(user.user_id),
        ),
    )


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page(request: Request):
    return templates.TemplateResponse(
        "privacy.html",
        _page_context(request, page_title="隐私与 AI 使用说明", user=None),
    )


@app.get("/student", response_class=HTMLResponse)
async def student_workspace(request: Request):
    user, redirect = _login_required(request)
    if redirect is not None:
        return redirect
    if user.account_role != "student":
        return RedirectResponse(url="/teacher", status_code=303)

    return templates.TemplateResponse(
        "student_dashboard.html",
        _page_context(
            request,
            page_title="学习空间",
            user=user.to_dict(),
            skills=list_assistant_skills("student"),
            learning_tasks=list_learning_tasks(user.user_id),
            learning_progress=get_learning_progress(user.user_id),
        ),
    )


@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    user, redirect = _login_required(request)
    if redirect is not None:
        return redirect

    return templates.TemplateResponse(
        "settings.html",
        _page_context(
            request,
            page_title="账号设置",
            user=user.to_dict(),
            success="",
            error="",
        ),
    )


@app.post("/settings", response_class=HTMLResponse)
async def settings_submit(request: Request):
    user, redirect = _login_required(request)
    if redirect is not None:
        return redirect

    form = await request.form()
    if not validate_csrf_token(request, form.get("csrf_token")):
        raise HTTPException(status_code=403, detail="页面已过期，请刷新后重试。")
    display_name = str(form.get("display_name", "")).strip()
    teacher_level = str(form.get("teacher_level", "")).strip()
    account_role = str(form.get("account_role", user.account_role)).strip()
    student_level = str(form.get("student_level", user.student_level)).strip()
    learning_goal = str(form.get("learning_goal", user.learning_goal)).strip()
    theme_name = str(form.get("theme_name", DEFAULT_THEME)).strip()
    password = str(form.get("password", "")).strip()
    teaching_languages = _normalize_form_languages(form.getlist("teaching_languages"))

    try:
        updated = update_account_profile(
            user.user_id,
            display_name=display_name,
            teaching_languages=teaching_languages,
            account_role=account_role,
            teacher_level=teacher_level,
            student_level=student_level,
            learning_goal=learning_goal,
            theme_name=theme_name,
            password=password or None,
        )
    except ValueError as exc:
        fallback_user = user.to_dict()
        fallback_user.update(
            {
                "display_name": display_name or user.display_name,
                "teaching_languages": teaching_languages,
                "account_role": account_role or user.account_role,
                "teacher_level": teacher_level or user.teacher_level,
                "student_level": student_level or user.student_level,
                "learning_goal": learning_goal or user.learning_goal,
                "theme_name": theme_name or user.theme_name,
            }
        )
        return templates.TemplateResponse(
            "settings.html",
            _page_context(
                request,
                page_title="账号设置",
                user=fallback_user,
                success="",
                error=str(exc),
            ),
            status_code=400,
        )

    if password:
        delete_user_sessions_for_user(user.user_id, exclude_session_id=request.cookies.get(SESSION_COOKIE_NAME))

    return templates.TemplateResponse(
        "settings.html",
        _page_context(
            request,
            page_title="账号设置",
            user=updated.to_dict(),
            success="设置已保存。",
            error="",
        ),
    )


@app.get("/api/me")
async def api_me(request: Request):
    user = _current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    return {"user": user.to_dict()}


@app.get("/api/skills")
async def api_skills(request: Request):
    user = _current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    return {"skills": list_assistant_skills(user.account_role)}


@app.post("/api/message")
async def api_message(request: Request, payload: AssistantMessageRequest):
    user = _current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    if not validate_csrf_token(request, request.headers.get("x-csrf-token")):
        raise HTTPException(status_code=403, detail="页面已过期，请刷新后重试。")
    allowed, retry_after = MESSAGE_LIMITER.allow(f"{client_key(request)}:{user.user_id}")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请在 {retry_after} 秒后重试。",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        reply = await run_in_threadpool(
            run_assistant_turn,
            skill_key=payload.skill_key,
            text=payload.text,
            profile=user,
            history=[item.model_dump() for item in payload.history],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="系统暂时不可用，请稍后重试。") from exc

    sources = get_haipai_source_cards(payload.text) if payload.skill_key in {"culture_explorer", "haipai_lesson_lab", "bridge_lesson_design"} else []
    return JSONResponse(
        {
            "reply": reply,
            "skill_key": payload.skill_key,
            "sources": sources,
        }
    )


@app.get("/api/student/tasks")
async def api_student_tasks(request: Request):
    user = _current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    if user.account_role != "student":
        raise HTTPException(status_code=403, detail="仅学习者可以访问学习任务。")
    return {
        "tasks": list_learning_tasks(user.user_id),
        "progress": get_learning_progress(user.user_id),
    }


@app.post("/api/student/tasks")
async def api_create_student_task(request: Request, payload: LearningTaskCreateRequest):
    user = _current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    if user.account_role != "student":
        raise HTTPException(status_code=403, detail="仅学习者可以保存学习任务。")
    if not validate_csrf_token(request, request.headers.get("x-csrf-token")):
        raise HTTPException(status_code=403, detail="页面已过期，请刷新后重试。")
    try:
        task = await run_in_threadpool(
            create_learning_task,
            user.user_id,
            topic=payload.topic,
            title=payload.title,
            prompt=payload.prompt,
            assistant_reply=payload.assistant_reply,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"task": task, "progress": get_learning_progress(user.user_id)}


@app.post("/api/student/tasks/{task_id}/complete")
async def api_complete_student_task(request: Request, task_id: str, payload: LearningTaskCompleteRequest):
    user = _current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    if user.account_role != "student":
        raise HTTPException(status_code=403, detail="仅学习者可以完成学习任务。")
    if not validate_csrf_token(request, request.headers.get("x-csrf-token")):
        raise HTTPException(status_code=403, detail="页面已过期，请刷新后重试。")
    try:
        task = await run_in_threadpool(complete_learning_task, user.user_id, task_id, payload.reflection)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "没有找到" in str(exc) else 400, detail=str(exc)) from exc
    return {"task": task, "progress": get_learning_progress(user.user_id)}


@app.get("/api/teacher/artifacts")
async def api_teacher_artifacts(request: Request):
    user = _current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    if user.account_role != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可以访问教案草稿。")
    return {"artifacts": list_teacher_artifacts(user.user_id)}


@app.post("/api/teacher/artifacts")
async def api_create_teacher_artifact(request: Request, payload: TeacherArtifactCreateRequest):
    user = _current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")
    if user.account_role != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可以保存教案草稿。")
    if not validate_csrf_token(request, request.headers.get("x-csrf-token")):
        raise HTTPException(status_code=403, detail="页面已过期，请刷新后重试。")
    try:
        artifact = await run_in_threadpool(
            create_teacher_artifact,
            user.user_id,
            title=payload.title,
            skill_key=payload.skill_key,
            prompt=payload.prompt,
            content=payload.content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"artifact": artifact}


@app.get("/teacher/artifacts/{artifact_id}", response_class=HTMLResponse)
async def teacher_artifact_page(request: Request, artifact_id: str):
    user, redirect = _login_required(request)
    if redirect is not None:
        return redirect
    if user.account_role != "teacher":
        return RedirectResponse(url="/student", status_code=303)
    artifact = get_teacher_artifact(user.user_id, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="没有找到这份教案草稿。")
    return templates.TemplateResponse(
        "artifact_print.html",
        _page_context(
            request,
            page_title=str(artifact["title"]),
            user=user.to_dict(),
            artifact=artifact,
            success=request.query_params.get("saved") == "1",
            error="",
        ),
    )


@app.post("/teacher/artifacts/{artifact_id}", response_class=HTMLResponse)
async def teacher_artifact_update(request: Request, artifact_id: str):
    user, redirect = _login_required(request)
    if redirect is not None:
        return redirect
    if user.account_role != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可以编辑教案草稿。")
    form = await request.form()
    if not validate_csrf_token(request, form.get("csrf_token")):
        raise HTTPException(status_code=403, detail="页面已过期，请刷新后重试。")
    try:
        await run_in_threadpool(
            update_teacher_artifact,
            user.user_id,
            artifact_id,
            title=str(form.get("title", "")),
            content=str(form.get("content", "")),
            review_status=str(form.get("review_status", "draft")),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404 if "没有找到" in str(exc) else 400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/teacher/artifacts/{artifact_id}?saved=1", status_code=303)


@app.get("/teacher/artifacts/{artifact_id}/download", response_class=PlainTextResponse)
async def teacher_artifact_download(request: Request, artifact_id: str):
    user, redirect = _login_required(request)
    if redirect is not None:
        return redirect
    if user.account_role != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可以导出教案草稿。")
    artifact = get_teacher_artifact(user.user_id, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="没有找到这份教案草稿。")
    markdown = (
        f"# {artifact['title']}\n\n"
        f"> 审核状态：{'教师已审核' if artifact['review_status'] == 'reviewed' else 'AI 草稿，待教师审核'}\n\n"
        f"## 原始教学需求\n\n{artifact['prompt']}\n\n"
        f"## 教案内容\n\n{artifact['content']}\n"
    )
    return PlainTextResponse(
        markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="zhiyuqiao-{artifact_id}.md"'},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "zhiyuqiao"}
