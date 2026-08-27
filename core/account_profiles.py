from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, get_db_session, init_database

DEFAULT_ACCOUNT_ID = "guest"
DEFAULT_THEME = "china_red"
DEFAULT_ACCOUNT_ROLE = "teacher"
DEFAULT_TEACHER_LEVEL = "experienced_teacher"
DEFAULT_STUDENT_LEVEL = "hsk3"
DEFAULT_LEARNING_GOAL = "culture_explorer"
SESSION_COOKIE_NAME = "zhiyuqiao_session"
SESSION_TTL_DAYS = int(os.getenv("ZHIYUQIAO_SESSION_TTL_DAYS", "7"))

TEACHER_LEVEL_LABELS = {
    "novice_teacher": "新手教师",
    "experienced_teacher": "成熟教师",
    "researcher": "教研人员",
}

ACCOUNT_ROLE_LABELS = {
    "student": "中文学习者",
    "teacher": "中文教师",
}

STUDENT_LEVEL_LABELS = {
    "starter": "刚开始学中文",
    "hsk1": "HSK 1",
    "hsk2": "HSK 2",
    "hsk3": "HSK 3",
    "hsk4": "HSK 4",
    "hsk5": "HSK 5",
    "hsk6": "HSK 6",
    "advanced": "高级学习者",
}

LEARNING_GOAL_LABELS = {
    "culture_explorer": "在上海学文化",
    "daily_chinese": "日常中文交流",
    "hsk_exam": "HSK 备考",
    "speaking": "提升口语表达",
    "writing": "提升中文写作",
}

THEME_LABELS = {
    "china_red": "中国红",
    "academy_blue": "学院蓝",
}

LANGUAGE_OPTIONS = (
    "中文",
    "English",
    "Português",
    "Español",
    "Français",
    "Deutsch",
    "日本語",
    "한국어",
)


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    password_salt: Mapped[str] = mapped_column(String(128))
    teaching_languages: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["中文"])
    primary_language: Mapped[str] = mapped_column(String(32), default="中文")
    account_role: Mapped[str] = mapped_column(String(16), default=DEFAULT_ACCOUNT_ROLE)
    teacher_level: Mapped[str] = mapped_column(String(32), default=DEFAULT_TEACHER_LEVEL)
    student_level: Mapped[str] = mapped_column(String(24), default=DEFAULT_STUDENT_LEVEL)
    learning_goal: Mapped[str] = mapped_column(String(32), default=DEFAULT_LEARNING_GOAL)
    theme_name: Mapped[str] = mapped_column(String(32), default=DEFAULT_THEME)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    sessions: Mapped[list["SessionRecord"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class SessionRecord(Base):
    __tablename__ = "user_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    user: Mapped[UserRecord] = relationship(back_populates="sessions")


class LearningTaskRecord(Base):
    __tablename__ = "learning_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(128))
    prompt: Mapped[str] = mapped_column(Text)
    assistant_reply: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="planned", index=True)
    reflection: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TeacherArtifactRecord(Base):
    __tablename__ = "teacher_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    skill_key: Mapped[str] = mapped_column(String(64))
    prompt: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(24), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class AccountProfile:
    user_id: str
    username: str
    display_name: str
    teaching_languages: tuple[str, ...]
    account_role: str
    teacher_level: str
    student_level: str
    learning_goal: str
    theme_name: str
    primary_language: str = "中文"
    region: str = ""
    school_stage: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def account_id(self) -> str:
        return self.username

    @property
    def instruction_language(self) -> str:
        if self.primary_language in self.teaching_languages:
            return self.primary_language
        return self.teaching_languages[0] if self.teaching_languages else "中文"

    @property
    def teaching_languages_display(self) -> str:
        return " / ".join(self.teaching_languages) if self.teaching_languages else "中文"

    @property
    def teacher_role(self) -> str:
        return self.teacher_level

    @property
    def teacher_role_label(self) -> str:
        return TEACHER_LEVEL_LABELS.get(self.teacher_level, self.teacher_level)

    @property
    def role_label(self) -> str:
        return ACCOUNT_ROLE_LABELS.get(self.account_role, self.account_role)

    @property
    def is_student(self) -> bool:
        return self.account_role == "student"

    @property
    def is_teacher(self) -> bool:
        return self.account_role == "teacher"

    @property
    def student_level_label(self) -> str:
        return STUDENT_LEVEL_LABELS.get(self.student_level, self.student_level)

    @property
    def learning_goal_label(self) -> str:
        return LEARNING_GOAL_LABELS.get(self.learning_goal, self.learning_goal)

    @property
    def workspace_url(self) -> str:
        return "/student" if self.is_student else "/teacher"

    @property
    def profile_level_label(self) -> str:
        return self.student_level_label if self.is_student else self.teacher_role_label

    @property
    def language_field_label(self) -> str:
        return "讲解语言" if self.is_student else "教学语种"

    @property
    def theme_label(self) -> str:
        return THEME_LABELS.get(self.theme_name, self.theme_name)

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["account_id"] = self.account_id
        payload["instruction_language"] = self.instruction_language
        payload["teaching_languages"] = list(self.teaching_languages)
        payload["teaching_languages_display"] = self.teaching_languages_display
        payload["teacher_role"] = self.teacher_role
        payload["teacher_role_label"] = self.teacher_role_label
        payload["role_label"] = self.role_label
        payload["is_student"] = self.is_student
        payload["is_teacher"] = self.is_teacher
        payload["student_level_label"] = self.student_level_label
        payload["learning_goal_label"] = self.learning_goal_label
        payload["workspace_url"] = self.workspace_url
        payload["profile_level_label"] = self.profile_level_label
        payload["language_field_label"] = self.language_field_label
        payload["theme_label"] = self.theme_label
        return payload


# Backward-compatible name for the retrieval and skill modules.
TeacherProfile = AccountProfile


def _normalize_languages(languages: Iterable[str] | str | None) -> tuple[str, ...]:
    if languages is None:
        return ("中文",)
    if isinstance(languages, str):
        raw_items = [item.strip() for item in languages.replace("，", ",").split(",")]
    else:
        raw_items = [str(item).strip() for item in languages]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        if not item:
            continue
        lowered = item.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(item)

    return tuple(normalized or ["中文"])


def _validate_teacher_level(teacher_level: str) -> str:
    cleaned = str(teacher_level or "").strip() or DEFAULT_TEACHER_LEVEL
    if cleaned not in TEACHER_LEVEL_LABELS:
        return DEFAULT_TEACHER_LEVEL
    return cleaned


def _validate_account_role(account_role: str) -> str:
    cleaned = str(account_role or "").strip() or DEFAULT_ACCOUNT_ROLE
    return cleaned if cleaned in ACCOUNT_ROLE_LABELS else DEFAULT_ACCOUNT_ROLE


def _validate_student_level(student_level: str) -> str:
    cleaned = str(student_level or "").strip() or DEFAULT_STUDENT_LEVEL
    return cleaned if cleaned in STUDENT_LEVEL_LABELS else DEFAULT_STUDENT_LEVEL


def _validate_learning_goal(learning_goal: str) -> str:
    cleaned = str(learning_goal or "").strip() or DEFAULT_LEARNING_GOAL
    return cleaned if cleaned in LEARNING_GOAL_LABELS else DEFAULT_LEARNING_GOAL


def _validate_theme_name(theme_name: str) -> str:
    cleaned = str(theme_name or "").strip() or DEFAULT_THEME
    if cleaned not in THEME_LABELS:
        return DEFAULT_THEME
    return cleaned


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt_value = salt or base64.urlsafe_b64encode(secrets.token_bytes(16)).decode("utf-8")
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        str(password).encode("utf-8"),
        salt_value.encode("utf-8"),
        390000,
    )
    password_hash = base64.urlsafe_b64encode(derived).decode("utf-8")
    return password_hash, salt_value


def _verify_password(password: str, password_hash: str, password_salt: str) -> bool:
    candidate_hash, _ = _hash_password(password, password_salt)
    return hmac.compare_digest(candidate_hash, password_hash)


def _record_to_profile(record: UserRecord) -> AccountProfile:
    languages = record.teaching_languages or ["中文"]
    created_at = record.created_at.isoformat() if record.created_at else ""
    updated_at = record.updated_at.isoformat() if record.updated_at else ""
    return AccountProfile(
        user_id=record.id,
        username=record.username,
        display_name=record.display_name,
        teaching_languages=tuple(languages),
        primary_language=(record.primary_language if record.primary_language in languages else languages[0]),
        account_role=_validate_account_role(record.account_role),
        teacher_level=record.teacher_level,
        student_level=_validate_student_level(record.student_level),
        learning_goal=_validate_learning_goal(record.learning_goal),
        theme_name=record.theme_name,
        created_at=created_at,
        updated_at=updated_at,
    )


def build_guest_profile() -> AccountProfile:
    return AccountProfile(
        user_id="guest",
        username=DEFAULT_ACCOUNT_ID,
        display_name="访客教师",
        teaching_languages=("中文",),
        account_role=DEFAULT_ACCOUNT_ROLE,
        teacher_level=DEFAULT_TEACHER_LEVEL,
        student_level=DEFAULT_STUDENT_LEVEL,
        learning_goal=DEFAULT_LEARNING_GOAL,
        theme_name=DEFAULT_THEME,
        primary_language="中文",
    )


def initialize_profile_store() -> None:
    init_database()


def count_users() -> int:
    initialize_profile_store()
    with get_db_session() as session:
        return len(session.scalars(select(UserRecord)).all())


def list_teacher_profiles() -> list[AccountProfile]:
    initialize_profile_store()
    with get_db_session() as session:
        records = session.scalars(select(UserRecord).order_by(UserRecord.created_at.asc())).all()
    return [_record_to_profile(record) for record in records]


def list_teacher_profile_choices() -> list[tuple[str, str]]:
    return [
        (
            f"{profile.display_name} · {profile.teaching_languages_display} · {profile.teacher_role_label}",
            profile.account_id,
        )
        for profile in list_teacher_profiles()
    ]


def get_teacher_profile(account_id: str | None = None) -> AccountProfile:
    initialize_profile_store()
    if not account_id:
        return build_guest_profile()

    resolved = str(account_id).strip()
    with get_db_session() as session:
        record = session.scalar(
            select(UserRecord).where(
                (UserRecord.id == resolved) | (UserRecord.username == resolved)
            )
        )
    if record is None:
        return build_guest_profile()
    return _record_to_profile(record)


def get_teacher_profile_by_identifier(identifier: str) -> AccountProfile | None:
    initialize_profile_store()
    resolved = str(identifier or "").strip()
    if not resolved:
        return None

    with get_db_session() as session:
        record = session.scalar(
            select(UserRecord).where(
                (UserRecord.username == resolved) | (UserRecord.display_name == resolved)
            )
        )
    return _record_to_profile(record) if record is not None else None


def register_teacher_account(
    username: str,
    display_name: str,
    password: str,
    teaching_languages: Sequence[str] | str | None,
    teacher_level: str,
    theme_name: str = DEFAULT_THEME,
) -> AccountProfile:
    return register_account(
        username=username,
        display_name=display_name,
        password=password,
        teaching_languages=teaching_languages,
        account_role="teacher",
        teacher_level=teacher_level,
        student_level=DEFAULT_STUDENT_LEVEL,
        learning_goal=DEFAULT_LEARNING_GOAL,
        theme_name=theme_name,
    )


def register_account(
    username: str,
    display_name: str,
    password: str,
    teaching_languages: Sequence[str] | str | None,
    account_role: str,
    teacher_level: str = DEFAULT_TEACHER_LEVEL,
    student_level: str = DEFAULT_STUDENT_LEVEL,
    learning_goal: str = DEFAULT_LEARNING_GOAL,
    theme_name: str = DEFAULT_THEME,
    primary_language: str | None = None,
) -> AccountProfile:
    initialize_profile_store()
    resolved_username = str(username or "").strip()
    resolved_display_name = str(display_name or "").strip()
    resolved_password = str(password or "")

    if not resolved_username or not resolved_display_name or not resolved_password:
        raise ValueError("账号、账号名和密码不能为空。")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", resolved_username):
        raise ValueError("登录账号须为3—32位英文字母、数字、点、下划线或连字符。")
    if not 1 <= len(resolved_display_name) <= 32:
        raise ValueError("显示名称须为1—32个字符。")
    if len(resolved_password) < 8:
        raise ValueError("密码至少需要8个字符。")

    normalized_languages = list(_normalize_languages(teaching_languages))
    resolved_primary_language = str(primary_language or "").strip()
    if resolved_primary_language not in normalized_languages:
        resolved_primary_language = normalized_languages[0]
    resolved_account_role = _validate_account_role(account_role)
    resolved_teacher_level = _validate_teacher_level(teacher_level)
    resolved_student_level = _validate_student_level(student_level)
    resolved_learning_goal = _validate_learning_goal(learning_goal)
    resolved_theme_name = _validate_theme_name(theme_name)
    password_hash, password_salt = _hash_password(resolved_password)

    with get_db_session() as session:
        existing_username = session.scalar(select(UserRecord).where(UserRecord.username == resolved_username))
        if existing_username is not None:
            raise ValueError("账号已存在，请更换一个账号。")

        existing_display_name = session.scalar(
            select(UserRecord).where(UserRecord.display_name == resolved_display_name)
        )
        if existing_display_name is not None:
            raise ValueError("账号名已存在，请更换一个账号名。")

        record = UserRecord(
            username=resolved_username,
            display_name=resolved_display_name,
            password_hash=password_hash,
            password_salt=password_salt,
            teaching_languages=normalized_languages,
            primary_language=resolved_primary_language,
            account_role=resolved_account_role,
            teacher_level=resolved_teacher_level,
            student_level=resolved_student_level,
            learning_goal=resolved_learning_goal,
            theme_name=resolved_theme_name,
        )
        session.add(record)
        session.flush()
        session.refresh(record)
        return _record_to_profile(record)


def authenticate_teacher(identifier: str, password: str) -> AccountProfile | None:
    initialize_profile_store()
    resolved_identifier = str(identifier or "").strip()
    resolved_password = str(password or "")
    if not resolved_identifier or not resolved_password:
        return None

    with get_db_session() as session:
        record = session.scalar(
            select(UserRecord).where(
                (UserRecord.username == resolved_identifier) | (UserRecord.display_name == resolved_identifier)
            )
        )
    if record is None:
        return None
    if not _verify_password(resolved_password, record.password_hash, record.password_salt):
        return None
    return _record_to_profile(record)


def update_teacher_profile(
    user_id: str,
    *,
    display_name: str,
    teaching_languages: Sequence[str] | str | None,
    teacher_level: str,
    theme_name: str,
    password: str | None = None,
) -> AccountProfile:
    return update_account_profile(
        user_id,
        display_name=display_name,
        teaching_languages=teaching_languages,
        account_role="teacher",
        teacher_level=teacher_level,
        student_level=DEFAULT_STUDENT_LEVEL,
        learning_goal=DEFAULT_LEARNING_GOAL,
        theme_name=theme_name,
        password=password,
    )


def update_account_profile(
    user_id: str,
    *,
    display_name: str,
    teaching_languages: Sequence[str] | str | None,
    account_role: str,
    teacher_level: str,
    student_level: str,
    learning_goal: str,
    theme_name: str,
    primary_language: str | None = None,
    password: str | None = None,
) -> AccountProfile:
    initialize_profile_store()
    resolved_user_id = str(user_id or "").strip()
    if not resolved_user_id:
        raise ValueError("用户不存在。")

    resolved_display_name = str(display_name or "").strip()
    if not resolved_display_name:
        raise ValueError("账号名不能为空。")
    if len(resolved_display_name) > 32:
        raise ValueError("显示名称不能超过32个字符。")
    if password and len(password) < 8:
        raise ValueError("新密码至少需要8个字符。")

    normalized_languages = list(_normalize_languages(teaching_languages))
    resolved_primary_language = str(primary_language or "").strip()
    if resolved_primary_language not in normalized_languages:
        resolved_primary_language = normalized_languages[0]
    resolved_account_role = _validate_account_role(account_role)
    resolved_teacher_level = _validate_teacher_level(teacher_level)
    resolved_student_level = _validate_student_level(student_level)
    resolved_learning_goal = _validate_learning_goal(learning_goal)
    resolved_theme_name = _validate_theme_name(theme_name)

    with get_db_session() as session:
        record = session.scalar(select(UserRecord).where(UserRecord.id == resolved_user_id))
        if record is None:
            raise ValueError("用户不存在。")

        duplicate = session.scalar(
            select(UserRecord).where(
                (UserRecord.display_name == resolved_display_name) & (UserRecord.id != resolved_user_id)
            )
        )
        if duplicate is not None:
            raise ValueError("账号名已存在，请更换一个账号名。")

        record.display_name = resolved_display_name
        record.teaching_languages = normalized_languages
        record.primary_language = resolved_primary_language
        record.account_role = resolved_account_role
        record.teacher_level = resolved_teacher_level
        record.student_level = resolved_student_level
        record.learning_goal = resolved_learning_goal
        record.theme_name = resolved_theme_name
        record.updated_at = datetime.now(timezone.utc)
        if password:
            record.password_hash, record.password_salt = _hash_password(password)

        session.add(record)
        session.flush()
        session.refresh(record)
        return _record_to_profile(record)


def delete_teacher_profile(account_id: str) -> None:
    initialize_profile_store()
    resolved = str(account_id or "").strip()
    if not resolved:
        return

    with get_db_session() as session:
        record = session.scalar(
            select(UserRecord).where(
                (UserRecord.id == resolved) | (UserRecord.username == resolved)
            )
        )
        if record is not None:
            session.delete(record)


def create_user_session(user_id: str) -> str:
    initialize_profile_store()
    session_id = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=SESSION_TTL_DAYS)

    with get_db_session() as session:
        record = SessionRecord(
            session_id=session_id,
            user_id=str(user_id),
            created_at=now,
            last_seen_at=now,
            expires_at=expires_at,
        )
        session.add(record)
    return session_id


def get_teacher_profile_by_session(session_id: str | None, *, touch: bool = True) -> AccountProfile | None:
    initialize_profile_store()
    resolved_session_id = str(session_id or "").strip()
    if not resolved_session_id:
        return None

    now = datetime.now(timezone.utc)
    with get_db_session() as session:
        record = session.scalar(select(SessionRecord).where(SessionRecord.session_id == resolved_session_id))
        if record is None:
            return None

        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            session.delete(record)
            return None

        if touch and (now - record.last_seen_at.replace(tzinfo=record.last_seen_at.tzinfo or timezone.utc)) >= timedelta(minutes=5):
            record.last_seen_at = now
            record.expires_at = now + timedelta(days=SESSION_TTL_DAYS)
            session.add(record)

        user = session.scalar(select(UserRecord).where(UserRecord.id == record.user_id))
        return _record_to_profile(user) if user is not None else None


def delete_user_session(session_id: str | None) -> None:
    initialize_profile_store()
    resolved_session_id = str(session_id or "").strip()
    if not resolved_session_id:
        return

    with get_db_session() as session:
        record = session.scalar(select(SessionRecord).where(SessionRecord.session_id == resolved_session_id))
        if record is not None:
            session.delete(record)


def delete_user_sessions_for_user(user_id: str, *, exclude_session_id: str | None = None) -> None:
    initialize_profile_store()
    resolved_user_id = str(user_id or "").strip()
    if not resolved_user_id:
        return
    with get_db_session() as session:
        records = session.scalars(select(SessionRecord).where(SessionRecord.user_id == resolved_user_id)).all()
        for record in records:
            if exclude_session_id and record.session_id == exclude_session_id:
                continue
            session.delete(record)


def delete_user_account(user_id: str, *, password: str, confirmation: str) -> None:
    """Permanently delete one account and its owned records after explicit verification."""
    initialize_profile_store()
    with get_db_session() as session:
        record = session.scalar(select(UserRecord).where(UserRecord.id == str(user_id)))
        if record is None:
            raise ValueError("用户不存在。")
        if not _verify_password(str(password or ""), record.password_hash, record.password_salt):
            raise ValueError("当前密码不正确。")
        if str(confirmation or "").strip() != record.username:
            raise ValueError("请输入完整登录账号以确认注销。")
        for task in session.scalars(select(LearningTaskRecord).where(LearningTaskRecord.user_id == record.id)).all():
            session.delete(task)
        for artifact in session.scalars(select(TeacherArtifactRecord).where(TeacherArtifactRecord.user_id == record.id)).all():
            session.delete(artifact)
        for user_session in session.scalars(select(SessionRecord).where(SessionRecord.user_id == record.id)).all():
            session.delete(user_session)
        session.delete(record)


def _task_to_dict(record: LearningTaskRecord) -> dict[str, object]:
    return {
        "id": record.id,
        "topic": record.topic,
        "title": record.title,
        "prompt": record.prompt,
        "assistant_reply": record.assistant_reply,
        "status": record.status,
        "reflection": record.reflection or "",
        "created_at": record.created_at.isoformat() if record.created_at else "",
        "completed_at": record.completed_at.isoformat() if record.completed_at else "",
    }


def list_learning_tasks(user_id: str, limit: int = 20) -> list[dict[str, object]]:
    initialize_profile_store()
    with get_db_session() as session:
        records = session.scalars(
            select(LearningTaskRecord)
            .where(LearningTaskRecord.user_id == str(user_id))
            .order_by(LearningTaskRecord.created_at.desc())
            .limit(max(1, min(int(limit), 50)))
        ).all()
    return [_task_to_dict(record) for record in records]


def get_learning_progress(user_id: str, total_topics: int = 6) -> dict[str, int]:
    initialize_profile_store()
    with get_db_session() as session:
        completed_topics = session.scalar(
            select(func.count(func.distinct(LearningTaskRecord.topic))).where(
                (LearningTaskRecord.user_id == str(user_id)) & (LearningTaskRecord.status == "completed")
            )
        ) or 0
    completed = min(int(completed_topics), max(1, int(total_topics)))
    return {
        "completed": completed,
        "total": max(1, int(total_topics)),
        "percent": round(completed / max(1, int(total_topics)) * 100),
    }


def create_learning_task(
    user_id: str,
    *,
    topic: str,
    title: str,
    prompt: str,
    assistant_reply: str,
) -> dict[str, object]:
    initialize_profile_store()
    record = LearningTaskRecord(
        user_id=str(user_id),
        topic=str(topic or "自主探索").strip()[:64] or "自主探索",
        title=str(title or "学习任务").strip()[:128] or "学习任务",
        prompt=str(prompt or "").strip()[:6000],
        assistant_reply=str(assistant_reply or "").strip()[:16000],
        status="planned",
    )
    with get_db_session() as session:
        count = session.scalar(select(func.count()).select_from(LearningTaskRecord).where(LearningTaskRecord.user_id == str(user_id))) or 0
        if count >= 50:
            raise ValueError("任务档案已达到50条，请先整理已有记录。")
        session.add(record)
        session.flush()
        session.refresh(record)
        return _task_to_dict(record)


def complete_learning_task(user_id: str, task_id: str, reflection: str) -> dict[str, object]:
    initialize_profile_store()
    resolved_reflection = str(reflection or "").strip()
    if len(resolved_reflection) < 2:
        raise ValueError("请用至少2个字符写下完成情况或学习收获。")
    with get_db_session() as session:
        record = session.scalar(
            select(LearningTaskRecord).where(
                (LearningTaskRecord.id == str(task_id)) & (LearningTaskRecord.user_id == str(user_id))
            )
        )
        if record is None:
            raise ValueError("没有找到这条学习任务。")
        record.status = "completed"
        record.reflection = resolved_reflection[:2000]
        record.completed_at = datetime.now(timezone.utc)
        session.add(record)
        session.flush()
        session.refresh(record)
        return _task_to_dict(record)


def _artifact_to_dict(record: TeacherArtifactRecord) -> dict[str, object]:
    return {
        "id": record.id,
        "title": record.title,
        "skill_key": record.skill_key,
        "prompt": record.prompt,
        "content": record.content,
        "review_status": record.review_status,
        "created_at": record.created_at.isoformat() if record.created_at else "",
        "updated_at": record.updated_at.isoformat() if record.updated_at else "",
    }


def list_teacher_artifacts(user_id: str, limit: int = 20) -> list[dict[str, object]]:
    initialize_profile_store()
    with get_db_session() as session:
        records = session.scalars(
            select(TeacherArtifactRecord)
            .where(TeacherArtifactRecord.user_id == str(user_id))
            .order_by(TeacherArtifactRecord.updated_at.desc())
            .limit(max(1, min(int(limit), 50)))
        ).all()
    return [_artifact_to_dict(record) for record in records]


def create_teacher_artifact(
    user_id: str,
    *,
    title: str,
    skill_key: str,
    prompt: str,
    content: str,
) -> dict[str, object]:
    initialize_profile_store()
    record = TeacherArtifactRecord(
        user_id=str(user_id),
        title=str(title or "教案草稿").strip()[:128] or "教案草稿",
        skill_key=str(skill_key or "teacher_advisor").strip()[:64],
        prompt=str(prompt or "").strip()[:6000],
        content=str(content or "").strip()[:30000],
        review_status="draft",
    )
    with get_db_session() as session:
        count = session.scalar(select(func.count()).select_from(TeacherArtifactRecord).where(TeacherArtifactRecord.user_id == str(user_id))) or 0
        if count >= 50:
            raise ValueError("教案草稿已达到50份，请先整理已有内容。")
        session.add(record)
        session.flush()
        session.refresh(record)
        return _artifact_to_dict(record)


def get_teacher_artifact(user_id: str, artifact_id: str) -> dict[str, object] | None:
    initialize_profile_store()
    with get_db_session() as session:
        record = session.scalar(
            select(TeacherArtifactRecord).where(
                (TeacherArtifactRecord.id == str(artifact_id)) & (TeacherArtifactRecord.user_id == str(user_id))
            )
        )
    return _artifact_to_dict(record) if record is not None else None


def update_teacher_artifact(
    user_id: str,
    artifact_id: str,
    *,
    title: str,
    content: str,
    review_status: str,
) -> dict[str, object]:
    initialize_profile_store()
    resolved_title = str(title or "").strip()
    resolved_content = str(content or "").strip()
    resolved_status = str(review_status or "draft").strip()
    if not resolved_title:
        raise ValueError("标题不能为空。")
    if not resolved_content:
        raise ValueError("教案内容不能为空。")
    if resolved_status not in {"draft", "reviewed"}:
        raise ValueError("无效的审核状态。")
    with get_db_session() as session:
        record = session.scalar(
            select(TeacherArtifactRecord).where(
                (TeacherArtifactRecord.id == str(artifact_id)) & (TeacherArtifactRecord.user_id == str(user_id))
            )
        )
        if record is None:
            raise ValueError("没有找到这份教案草稿。")
        record.title = resolved_title[:128]
        record.content = resolved_content[:30000]
        record.review_status = resolved_status
        record.updated_at = datetime.now(timezone.utc)
        session.add(record)
        session.flush()
        session.refresh(record)
        return _artifact_to_dict(record)
