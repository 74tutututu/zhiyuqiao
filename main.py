from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from core.account_profiles import (
    DEFAULT_THEME,
    LANGUAGE_OPTIONS,
    SESSION_COOKIE_NAME,
    SESSION_TTL_DAYS,
    TEACHER_LEVEL_LABELS,
    THEME_LABELS,
    authenticate_teacher,
    count_users,
    create_user_session,
    delete_user_session,
    get_teacher_profile_by_session,
    initialize_profile_store,
    register_teacher_account,
    update_teacher_profile,
)
from core.assistant_service import list_assistant_skills, run_assistant_turn

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


class AssistantMessageRequest(BaseModel):
    skill_key: str = Field(default="teacher_advisor", description="当前选择的 skill")
    text: str = Field(..., description="用户输入")
    history: list[dict[str, Any]] | None = Field(default=None, description="当前会话历史")


def _theme_choices() -> list[tuple[str, str]]:
    return [(value, key) for key, value in THEME_LABELS.items()]


def _teacher_level_choices() -> list[tuple[str, str]]:
    return [(value, key) for key, value in TEACHER_LEVEL_LABELS.items()]


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
        "teacher_level_choices": _teacher_level_choices(),
        "theme_choices": _theme_choices(),
        "default_theme": DEFAULT_THEME,
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
        max_age=SESSION_TTL_DAYS * 24 * 60 * 60,
        path="/",
    )
    return response


def _login_required(request: Request):
    user = _current_user(request)
    if user is None:
        return None, RedirectResponse(url="/login", status_code=303)
    return user, None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = _current_user(request)
    if user is not None:
        return RedirectResponse(url="/assistant", status_code=303)
    if count_users() == 0:
        return RedirectResponse(url="/register", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if _current_user(request) is not None:
        return RedirectResponse(url="/assistant", status_code=303)

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
    if _current_user(request) is not None:
        return RedirectResponse(url="/assistant", status_code=303)

    form = await request.form()
    form_data = {
        "username": str(form.get("username", "")).strip(),
        "display_name": str(form.get("display_name", "")).strip(),
        "teacher_level": str(form.get("teacher_level", "")).strip(),
        "theme_name": str(form.get("theme_name", DEFAULT_THEME)).strip(),
    }
    teaching_languages = _normalize_form_languages(form.getlist("teaching_languages"))
    password = str(form.get("password", ""))

    try:
        profile = register_teacher_account(
            username=form_data["username"],
            display_name=form_data["display_name"],
            password=password,
            teaching_languages=teaching_languages,
            teacher_level=form_data["teacher_level"],
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
    return _redirect_with_session("/assistant", session_id)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _current_user(request) is not None:
        return RedirectResponse(url="/assistant", status_code=303)
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
    identifier = str(form.get("identifier", "")).strip()
    password = str(form.get("password", ""))

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
    return _redirect_with_session("/assistant", session_id)


@app.post("/logout")
async def logout(request: Request):
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

    return templates.TemplateResponse(
        "assistant.html",
        _page_context(
            request,
            page_title="智语桥",
            user=user.to_dict(),
            skills=list_assistant_skills(),
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
    display_name = str(form.get("display_name", "")).strip()
    teacher_level = str(form.get("teacher_level", "")).strip()
    theme_name = str(form.get("theme_name", DEFAULT_THEME)).strip()
    password = str(form.get("password", "")).strip()
    teaching_languages = _normalize_form_languages(form.getlist("teaching_languages"))

    try:
        updated = update_teacher_profile(
            user.user_id,
            display_name=display_name,
            teaching_languages=teaching_languages,
            teacher_level=teacher_level,
            theme_name=theme_name,
            password=password or None,
        )
    except ValueError as exc:
        fallback_user = user.to_dict()
        fallback_user.update(
            {
                "display_name": display_name or user.display_name,
                "teaching_languages": teaching_languages,
                "teacher_level": teacher_level or user.teacher_level,
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
    return {"skills": list_assistant_skills()}


@app.post("/api/message")
async def api_message(request: Request, payload: AssistantMessageRequest):
    user = _current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="未登录")

    try:
        reply = run_assistant_turn(
            skill_key=payload.skill_key,
            text=payload.text,
            profile=user,
            history=payload.history,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"系统暂时不可用：{str(exc)}") from exc

    return JSONResponse(
        {
            "reply": reply,
            "skill_key": payload.skill_key,
        }
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
