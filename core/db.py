from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_URL = f"sqlite:///{PROJECT_ROOT / 'database' / 'zhiyuqiao_dev.sqlite3'}"


def _resolve_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL).strip() or DEFAULT_SQLITE_URL


DATABASE_URL = _resolve_database_url()

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


class Base(DeclarativeBase):
    pass


@contextmanager
def get_db_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_user_profile_columns()


def _migrate_user_profile_columns() -> None:
    """Add role-aware profile fields without discarding existing local accounts."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("users")}
    statements: list[str] = []
    if "account_role" not in existing:
        statements.append(
            "ALTER TABLE users ADD COLUMN account_role VARCHAR(16) NOT NULL DEFAULT 'teacher'"
        )
    if "student_level" not in existing:
        statements.append(
            "ALTER TABLE users ADD COLUMN student_level VARCHAR(24) NOT NULL DEFAULT 'hsk3'"
        )
    if "learning_goal" not in existing:
        statements.append(
            "ALTER TABLE users ADD COLUMN learning_goal VARCHAR(32) NOT NULL DEFAULT 'culture_explorer'"
        )
    if "primary_language" not in existing:
        statements.append(
            "ALTER TABLE users ADD COLUMN primary_language VARCHAR(32) NOT NULL DEFAULT '中文'"
        )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
