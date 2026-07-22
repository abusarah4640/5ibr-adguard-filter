"""Authentication and per-user preferences for the web application."""

from __future__ import annotations

import os
import re
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


@dataclass
class User(UserMixin):
    id: int
    username: str
    display_name: str
    email: str
    role: str
    language: str
    theme: str
    timezone: str
    date_format: str
    session_version: str = ""
    active: bool = True

    @property
    def is_active(self) -> bool:
        return self.active

    def get_id(self) -> str:
        return f"{self.id}:{self.session_version}"

    def has_role(self, *roles: str) -> bool:
        return self.role in roles


class UserStore:
    """Small SQLite-backed user store, isolated from the project data schema."""

    def __init__(self, path: Path):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS web_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL DEFAULT '',
                    email TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL DEFAULT 'viewer',
                    language TEXT NOT NULL DEFAULT 'en',
                    theme TEXT NOT NULL DEFAULT 'auto',
                    timezone TEXT NOT NULL DEFAULT 'UTC',
                    date_format TEXT NOT NULL DEFAULT 'yyyy-mm-dd',
                    session_version TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1
                )"""
            )
            columns = {
                row["name"]
                for row in db.execute("PRAGMA table_info(web_users)")
            }
            if "session_version" not in columns:
                db.execute(
                    "ALTER TABLE web_users "
                    "ADD COLUMN session_version TEXT NOT NULL DEFAULT ''"
                )
            missing_versions = db.execute(
                "SELECT id FROM web_users WHERE session_version = ''"
            ).fetchall()
            for row in missing_versions:
                db.execute(
                    "UPDATE web_users SET session_version = ? WHERE id = ?",
                    (secrets.token_urlsafe(32), row["id"]),
                )
            count = db.execute("SELECT COUNT(*) FROM web_users").fetchone()[0]
            bootstrap_password = os.environ.get("FIVEBR_ADMIN_PASSWORD")
            if count == 0 and bootstrap_password:
                self.create_user(
                    "admin", bootstrap_password, role="admin", display_name="Administrator"
                )

    @staticmethod
    def _user(row: sqlite3.Row | None) -> User | None:
        if row is None:
            return None
        return User(
            id=row["id"], username=row["username"], display_name=row["display_name"],
            email=row["email"], role=row["role"], language=row["language"],
            theme=row["theme"], timezone=row["timezone"], date_format=row["date_format"],
            session_version=row["session_version"],
            active=bool(row["active"]),
        )

    def get(self, user_id: str | int) -> User | None:
        with self.connect() as db:
            return self._user(db.execute("SELECT * FROM web_users WHERE id = ?", (user_id,)).fetchone())

    def get_for_session(self, identity: str) -> User | None:
        user_id, separator, session_version = identity.partition(":")
        if not separator or not user_id.isdigit() or not session_version:
            return None
        user = self.get(user_id)
        if (
            user is None
            or not user.active
            or not secrets.compare_digest(
                user.session_version,
                session_version,
            )
        ):
            return None
        return user

    def has_users(self) -> bool:
        with self.connect() as db:
            return bool(db.execute("SELECT EXISTS(SELECT 1 FROM web_users)").fetchone()[0])

    def authenticate(self, username: str, password: str) -> User | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM web_users WHERE username = ?", (username.strip(),)).fetchone()
        if row and bool(row["active"]) and check_password_hash(row["password_hash"], password):
            return self._user(row)
        return None

    def create_user(self, username: str, password: str, *, role: str = "viewer", display_name: str = "") -> int:
        username = username.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", username):
            raise ValueError("Username must be 3-64 letters, numbers, dots, dashes, or underscores")
        if role not in {"admin", "editor", "viewer"}:
            raise ValueError("Invalid role")
        if len(password) < 12:
            raise ValueError("Password must contain at least 12 characters")
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO web_users "
                "(username, password_hash, display_name, role, session_version) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    username,
                    generate_password_hash(password),
                    display_name.strip()[:120],
                    role,
                    secrets.token_urlsafe(32),
                ),
            )
            return int(cursor.lastrowid)

    def update_profile(self, user_id: int, **values: str) -> None:
        allowed = {"display_name", "email", "language", "theme", "timezone", "date_format"}
        values = {key: value for key, value in values.items() if key in allowed}
        if not values:
            return
        assignments = ", ".join(f"{key} = ?" for key in values)
        with self.connect() as db:
            db.execute(f"UPDATE web_users SET {assignments} WHERE id = ?", (*values.values(), user_id))

    def change_password(self, user_id: int, current: str, new: str) -> bool:
        if len(new) < 12:
            raise ValueError("Password must contain at least 12 characters")
        with self.connect() as db:
            row = db.execute("SELECT password_hash FROM web_users WHERE id = ?", (user_id,)).fetchone()
            if not row or not check_password_hash(row["password_hash"], current):
                return False
            db.execute(
                "UPDATE web_users "
                "SET password_hash = ?, session_version = ? "
                "WHERE id = ?",
                (
                    generate_password_hash(new),
                    secrets.token_urlsafe(32),
                    user_id,
                ),
            )
        return True

    def set_role(self, user_id: int, role: str) -> None:
        if role not in {"admin", "editor", "viewer"}:
            raise ValueError("Invalid role")
        with self.connect() as db:
            db.execute(
                "UPDATE web_users "
                "SET role = ?, session_version = ? "
                "WHERE id = ?",
                (role, secrets.token_urlsafe(32), user_id),
            )

    def set_active(self, user_id: int, active: bool) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE web_users "
                "SET active = ?, session_version = ? "
                "WHERE id = ?",
                (int(active), secrets.token_urlsafe(32), user_id),
            )
