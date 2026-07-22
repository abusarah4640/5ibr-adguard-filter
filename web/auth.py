"""Authentication and per-user preferences for the web application."""

from __future__ import annotations

import os
import re
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
    active: bool = True

    @property
    def is_active(self) -> bool:
        return self.active

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
                    active INTEGER NOT NULL DEFAULT 1
                )"""
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
            active=bool(row["active"]),
        )

    def get(self, user_id: str | int) -> User | None:
        with self.connect() as db:
            return self._user(db.execute("SELECT * FROM web_users WHERE id = ?", (user_id,)).fetchone())

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
                "INSERT INTO web_users (username, password_hash, display_name, role) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash(password), display_name.strip()[:120], role),
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
            db.execute("UPDATE web_users SET password_hash = ? WHERE id = ?", (generate_password_hash(new), user_id))
        return True
