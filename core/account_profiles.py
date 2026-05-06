from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Sequence

from sqlalchemy import JSON, DateTime, ForeignKey, String, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, get_db_session, init_database

DEFAULT_ACCOUNT_ID = "guest"
DEFAULT_THEME = "china_red"
DEFAULT_TEACHER_LEVEL = "experienced_teacher"
SESSION_COOKIE_NAME = "zhiyuqiao_session"
SESSION_TTL_DAYS = int(os.getenv("ZHIYUQIAO_SESSION_TTL_DAYS", "7"))

TEACHER_LEVEL_LABELS = {
    "novice_teacher": "新手教师",
    "experienced_teacher": "成熟教师",
    "researcher": "教研人员",
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
    teacher_level: Mapped[str] = mapped_column(String(32), default=DEFAULT_TEACHER_LEVEL)
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


@dataclass(frozen=True)
class TeacherProfile:
    user_id: str
    username: str
    display_name: str
    teaching_languages: tuple[str, ...]
    teacher_level: str
    theme_name: str
    region: str = ""
    school_stage: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def account_id(self) -> str:
        return self.username

    @property
    def instruction_language(self) -> str:
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
    def theme_label(self) -> str:
        return THEME_LABELS.get(self.theme_name, self.theme_name)

    def to_dict(self) -> dict[str, str | list[str]]:
        payload = asdict(self)
        payload["account_id"] = self.account_id
        payload["instruction_language"] = self.instruction_language
        payload["teaching_languages"] = list(self.teaching_languages)
        payload["teaching_languages_display"] = self.teaching_languages_display
        payload["teacher_role"] = self.teacher_role
        payload["teacher_role_label"] = self.teacher_role_label
        payload["theme_label"] = self.theme_label
        return payload


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


def _record_to_profile(record: UserRecord) -> TeacherProfile:
    languages = record.teaching_languages or ["中文"]
    created_at = record.created_at.isoformat() if record.created_at else ""
    updated_at = record.updated_at.isoformat() if record.updated_at else ""
    return TeacherProfile(
        user_id=record.id,
        username=record.username,
        display_name=record.display_name,
        teaching_languages=tuple(languages),
        teacher_level=record.teacher_level,
        theme_name=record.theme_name,
        created_at=created_at,
        updated_at=updated_at,
    )


def build_guest_profile() -> TeacherProfile:
    return TeacherProfile(
        user_id="guest",
        username=DEFAULT_ACCOUNT_ID,
        display_name="访客教师",
        teaching_languages=("中文",),
        teacher_level=DEFAULT_TEACHER_LEVEL,
        theme_name=DEFAULT_THEME,
    )


def initialize_profile_store() -> None:
    init_database()


def count_users() -> int:
    initialize_profile_store()
    with get_db_session() as session:
        return len(session.scalars(select(UserRecord)).all())


def list_teacher_profiles() -> list[TeacherProfile]:
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


def get_teacher_profile(account_id: str | None = None) -> TeacherProfile:
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


def get_teacher_profile_by_identifier(identifier: str) -> TeacherProfile | None:
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
) -> TeacherProfile:
    initialize_profile_store()
    resolved_username = str(username or "").strip()
    resolved_display_name = str(display_name or "").strip()
    resolved_password = str(password or "")

    if not resolved_username or not resolved_display_name or not resolved_password:
        raise ValueError("账号、账号名和密码不能为空。")

    normalized_languages = list(_normalize_languages(teaching_languages))
    resolved_teacher_level = _validate_teacher_level(teacher_level)
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
            teacher_level=resolved_teacher_level,
            theme_name=resolved_theme_name,
        )
        session.add(record)
        session.flush()
        session.refresh(record)
        return _record_to_profile(record)


def authenticate_teacher(identifier: str, password: str) -> TeacherProfile | None:
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
) -> TeacherProfile:
    initialize_profile_store()
    resolved_user_id = str(user_id or "").strip()
    if not resolved_user_id:
        raise ValueError("用户不存在。")

    resolved_display_name = str(display_name or "").strip()
    if not resolved_display_name:
        raise ValueError("账号名不能为空。")

    normalized_languages = list(_normalize_languages(teaching_languages))
    resolved_teacher_level = _validate_teacher_level(teacher_level)
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
        record.teacher_level = resolved_teacher_level
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


def get_teacher_profile_by_session(session_id: str | None, *, touch: bool = True) -> TeacherProfile | None:
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

        if touch:
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
