import sqlite3
import subprocess
from io import BytesIO
from pathlib import Path

import re
from datetime import timedelta

import pytest

from web.app import create_app, main
from web.auth import UserStore


def security_app(tmp_path, **config):
    values = {
        "TESTING": True,
        "INSECURE_TEST_BYPASS": False,
        "SECRET_KEY": "security-test-secret",
        "USER_DATABASE": tmp_path / "security-users.sqlite3",
    }
    values.update(config)
    return create_app(values)


def token_from(response) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match
    return match.group(1)


def login(client, username: str, password: str):
    token = token_from(client.get("/login"))
    return client.post("/login", data={
        "csrf_token": token, "username": username, "password": password,
    })




def test_analyze_log_rejects_free_server_path(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    monkeypatch.setattr("web.app.UPLOADS_DIR", uploads)
    app = security_app(tmp_path)
    app.extensions["fivebr_users"].create_user(
        "editor-path",
        "editor-password-123",
        role="editor",
    )
    client = app.test_client()
    assert login(client, "editor-path", "editor-password-123").status_code == 302
    token = token_from(client.get("/analyze-log"))
    calls = []
    monkeypatch.setattr(
        "web.app.subprocess.run",
        lambda command, **kwargs: (
            calls.append(tuple(command))
            or subprocess.CompletedProcess(
                command,
                0,
                stdout="unexpected",
                stderr="",
            )
        ),
    )

    response = client.post(
        "/analyze-log",
        data={
            "csrf_token": token,
            "path": "/etc/passwd",
            "min_seen": "10",
            "limit": "100",
        },
    )

    assert response.status_code == 200
    assert calls == []
    assert list(uploads.iterdir()) == []


def test_analyze_log_uses_server_generated_upload_path(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    calls = []
    monkeypatch.setattr("web.app.UPLOADS_DIR", uploads)
    monkeypatch.setattr(
        "web.app.subprocess.run",
        lambda command, **kwargs: (
            calls.append(tuple(command))
            or subprocess.CompletedProcess(
                command,
                0,
                stdout="ok",
                stderr="",
            )
        ),
    )
    monkeypatch.setattr("web.app.create_backup", lambda *args: None)
    monkeypatch.setattr("web.app.log_event", lambda *args: None)
    app = security_app(tmp_path)
    app.extensions["fivebr_users"].create_user(
        "editor-upload",
        "editor-password-123",
        role="editor",
    )
    client = app.test_client()
    assert login(client, "editor-upload", "editor-password-123").status_code == 302
    token = token_from(client.get("/analyze-log"))

    response = client.post(
        "/analyze-log",
        data={
            "csrf_token": token,
            "path": "/etc/passwd",
            "min_seen": "10",
            "limit": "100",
            "querylog": (
                BytesIO(b"{\"data\": []}"),
                "../../querylog.json",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0][3] == "analyze-log"
    uploaded = Path(calls[0][4]).resolve()
    assert uploaded.is_relative_to(uploads.resolve())
    assert uploaded.parent == uploads.resolve()
    assert uploaded.name != "querylog.json"
    assert uploaded.suffix == ".json"
    assert uploaded.read_bytes() == b"{\"data\": []}"


@pytest.mark.parametrize("path", [
    "/",
    "/intelligence",
    "/domains",
    "/analysis",
    "/review-queue",
    "/reports/suggestions",
    "/reports/suggestions.md",
    "/releases",
    "/audit",
    "/releases/example.txt",
])
def test_sensitive_get_routes_require_authentication(tmp_path, path):
    app = security_app(tmp_path)
    response = app.test_client().get(path)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


@pytest.mark.parametrize(("path", "data"), [

    ("/logout", {}), ("/settings", {}), ("/settings/password", {}),
    ("/readiness/manual-approval", {}), ("/domains/add", {}),
    ("/domains/example.test/edit", {}), ("/domains/example.test/delete", {}),
    ("/actions/validate", {}), ("/analyze", {}), ("/analyze-log", {}),
    ("/review-queue/example.test/rejected", {}),
    ("/suggestions/example.test/approve", {}),
    ("/suggestions/example.test/reject", {}),
])
def test_every_post_route_rejects_missing_csrf(tmp_path, path, data):
    app = security_app(tmp_path)
    response = app.test_client().post(path, data=data)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_post_still_rejects_missing_csrf(tmp_path):
    app = security_app(tmp_path)
    response = app.test_client().post("/login", data={"username": "x", "password": "x"})
    assert response.status_code == 400


def test_login_rotates_anonymous_session_and_csrf(tmp_path):
    app = security_app(tmp_path)
    app.extensions["fivebr_users"].create_user(
        "csrf-viewer",
        "csrf-password-123",
        role="viewer",
    )
    client = app.test_client()
    anonymous_token = token_from(client.get("/login"))

    response = client.post(
        "/login",
        data={
            "csrf_token": anonymous_token,
            "username": "csrf-viewer",
            "password": "csrf-password-123",
        },
    )

    assert response.status_code == 302
    authenticated_token = token_from(client.get("/"))
    assert authenticated_token != anonymous_token
    assert client.post(
        "/actions/validate",
        data={"csrf_token": anonymous_token},
    ).status_code == 400
    assert client.post(
        "/actions/validate",
        data={"csrf_token": authenticated_token},
    ).status_code == 403


def test_logout_rotates_session_and_clears_remember_cookie(tmp_path):
    app = security_app(tmp_path)
    app.extensions["fivebr_users"].create_user(
        "remember-owner",
        "remember-password-123",
        role="admin",
    )
    client = app.test_client()
    anonymous_token = token_from(client.get("/login"))
    logged_in = client.post(
        "/login",
        data={
            "csrf_token": anonymous_token,
            "username": "remember-owner",
            "password": "remember-password-123",
            "remember": "on",
        },
    )
    assert logged_in.status_code == 302
    authenticated_token = token_from(client.get("/"))

    logged_out = client.post(
        "/logout",
        data={"csrf_token": authenticated_token},
    )

    assert logged_out.status_code == 302
    cookies = logged_out.headers.getlist("Set-Cookie")
    assert any(
        cookie.startswith("fivebr_remember=")
        and ("Max-Age=0" in cookie or "Expires=Thu, 01 Jan 1970" in cookie)
        for cookie in cookies
    )
    assert client.get("/").status_code == 302
    post_logout_token = token_from(client.get("/login"))
    assert post_logout_token != authenticated_token


def test_login_rate_limit_blocks_repeated_failures(tmp_path):
    app = security_app(
        tmp_path,
        LOGIN_FAILURE_LIMIT=3,
        LOGIN_FAILURE_WINDOW_SECONDS=900,
        LOGIN_BLOCK_SECONDS=120,
    )
    app.extensions["fivebr_users"].create_user(
        "limited-owner",
        "limited-password-123",
        role="admin",
    )
    client = app.test_client()
    token = token_from(client.get("/login"))

    for _ in range(2):
        response = client.post(
            "/login",
            data={
                "csrf_token": token,
                "username": "limited-owner",
                "password": "wrong-password",
            },
            environ_base={"REMOTE_ADDR": "198.51.100.10"},
        )
        assert response.status_code == 200

    blocked = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "limited-owner",
            "password": "wrong-password",
        },
        environ_base={"REMOTE_ADDR": "198.51.100.10"},
    )
    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers["Retry-After"]) <= 120

    correct_password_is_still_blocked = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "limited-owner",
            "password": "limited-password-123",
        },
        environ_base={"REMOTE_ADDR": "198.51.100.10"},
    )
    assert correct_password_is_still_blocked.status_code == 429


def test_login_rate_limit_ignores_forwarded_address_and_clears_on_success(
    tmp_path,
):
    app = security_app(
        tmp_path,
        LOGIN_FAILURE_LIMIT=2,
        LOGIN_FAILURE_WINDOW_SECONDS=900,
        LOGIN_BLOCK_SECONDS=120,
    )
    store = app.extensions["fivebr_users"]
    store.create_user(
        "successful-owner",
        "successful-password-123",
        role="admin",
    )
    client = app.test_client()
    token = token_from(client.get("/login"))

    failed = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "successful-owner",
            "password": "wrong-password",
        },
        headers={"X-Forwarded-For": "203.0.113.1"},
        environ_base={"REMOTE_ADDR": "198.51.100.20"},
    )
    assert failed.status_code == 200

    successful = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "successful-owner",
            "password": "successful-password-123",
        },
        headers={"X-Forwarded-For": "203.0.113.200"},
        environ_base={"REMOTE_ADDR": "198.51.100.20"},
    )
    assert successful.status_code == 302

    with store.connect() as db:
        remaining = db.execute(
            "SELECT COUNT(*) FROM web_login_attempts"
        ).fetchone()[0]
    assert remaining == 0


def test_production_requires_trusted_hosts(tmp_path, monkeypatch):
    monkeypatch.setenv("FIVEBR_ENV", "production")
    monkeypatch.setenv("FIVEBR_SECRET_KEY", "production-test-secret")
    monkeypatch.delenv("FIVEBR_TRUSTED_HOSTS", raising=False)

    with pytest.raises(
        RuntimeError,
        match="FIVEBR_TRUSTED_HOSTS is required",
    ):
        create_app({
            "USER_DATABASE": tmp_path / "production-users.sqlite3",
        })


def test_production_accepts_explicit_trusted_hosts(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("FIVEBR_ENV", "production")
    monkeypatch.setenv("FIVEBR_SECRET_KEY", "production-test-secret")
    monkeypatch.setenv(
        "FIVEBR_TRUSTED_HOSTS",
        "filters.example.test, admin.example.test",
    )

    app = create_app({
        "USER_DATABASE": tmp_path / "production-users.sqlite3",
    })

    assert app.config["TRUSTED_HOSTS"] == [
        "filters.example.test",
        "admin.example.test",
    ]


def test_language_cookie_is_httponly(tmp_path):
    app = security_app(tmp_path)
    response = app.test_client().get("/language/ar")
    cookies = response.headers.getlist("Set-Cookie")

    language_cookie = next(
        cookie
        for cookie in cookies
        if cookie.startswith("fivebr_lang=")
    )
    assert "HttpOnly" in language_cookie
    assert "SameSite=Lax" in language_cookie


def test_development_entrypoint_binds_loopback_only(monkeypatch):
    calls = []
    monkeypatch.delenv("FIVEBR_ENV", raising=False)
    monkeypatch.setenv("FIVEBR_DEV_PORT", "8090")
    monkeypatch.setattr(
        "web.app.app.run",
        lambda **kwargs: calls.append(kwargs),
    )

    assert main() == 0
    assert calls == [{"host": "127.0.0.1", "port": 8090}]


def test_development_entrypoint_refuses_production(monkeypatch):
    calls = []
    monkeypatch.setenv("FIVEBR_ENV", "production")
    monkeypatch.setattr(
        "web.app.app.run",
        lambda **kwargs: calls.append(kwargs),
    )

    with pytest.raises(RuntimeError, match="development server is disabled"):
        main()

    assert calls == []


def test_testing_mode_alone_does_not_bypass_security(tmp_path):
    app = create_app({
        "TESTING": True,
        "INSECURE_TEST_BYPASS": False,
        "SECRET_KEY": "testing-with-real-security",
        "USER_DATABASE": tmp_path / "testing-users.sqlite3",
    })
    client = app.test_client()

    protected = client.get("/")
    assert protected.status_code == 302
    assert "/login" in protected.headers["Location"]

    login_without_csrf = client.post(
        "/login",
        data={"username": "x", "password": "x"},
    )
    assert login_without_csrf.status_code == 400


def test_empty_user_database_fails_closed(tmp_path):
    app = security_app(tmp_path)
    client = app.test_client()
    token = token_from(client.get("/login"))
    response = client.post("/actions/validate", data={"csrf_token": token})
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_viewer_cannot_mutate_and_editor_cannot_build(tmp_path):
    app = security_app(tmp_path)
    store = app.extensions["fivebr_users"]
    store.create_user("viewer", "viewer-password-123", role="viewer")
    store.create_user("editor", "editor-password-123", role="editor")

    viewer = app.test_client()
    assert login(viewer, "viewer", "viewer-password-123").status_code == 302
    token = token_from(viewer.get("/"))
    assert viewer.post("/actions/validate", data={"csrf_token": token}).status_code == 403
    assert viewer.get("/domains/add").status_code == 403

    editor = app.test_client()
    assert login(editor, "editor", "editor-password-123").status_code == 302
    token = token_from(editor.get("/"))
    assert editor.post("/actions/build", data={"csrf_token": token}).status_code == 403
    assert editor.get("/domains/add").status_code == 200


def test_legacy_user_database_migrates_session_versions(tmp_path):
    database = tmp_path / "legacy-users.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute(
            """CREATE TABLE web_users (
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
        db.execute(
            "INSERT INTO web_users (username, password_hash) VALUES (?, ?)",
            ("legacy-user", "legacy-hash"),
        )

    store = UserStore(database)
    store.initialize()
    user = store.get(1)

    assert user is not None
    assert user.session_version
    assert store.get_for_session(str(user.id)) is None
    assert store.get_for_session(user.get_id()) is not None


def test_password_change_revokes_parallel_and_remembered_sessions(tmp_path):
    app = security_app(tmp_path)
    store = app.extensions["fivebr_users"]
    store.create_user(
        "session-owner",
        "old-password-123",
        role="admin",
    )

    primary = app.test_client()
    parallel = app.test_client()
    remembered = app.test_client()
    assert login(primary, "session-owner", "old-password-123").status_code == 302
    assert login(parallel, "session-owner", "old-password-123").status_code == 302

    remember_token = token_from(remembered.get("/login"))
    remember_response = remembered.post(
        "/login",
        data={
            "csrf_token": remember_token,
            "username": "session-owner",
            "password": "old-password-123",
            "remember": "on",
        },
    )
    assert remember_response.status_code == 302
    remembered.delete_cookie(app.config["SESSION_COOKIE_NAME"])
    assert remembered.get("/").status_code == 200
    remembered.delete_cookie(app.config["SESSION_COOKIE_NAME"])

    token = token_from(primary.get("/settings"))
    changed = primary.post(
        "/settings/password",
        data={
            "csrf_token": token,
            "current_password": "old-password-123",
            "new_password": "new-password-456",
            "confirm_password": "new-password-456",
        },
    )

    assert changed.status_code == 302
    assert changed.headers["Location"].endswith("/login")
    assert parallel.get("/").status_code == 302
    assert "/login" in parallel.get("/").headers["Location"]
    assert remembered.get("/").status_code == 302
    assert "/login" in remembered.get("/").headers["Location"]
    assert login(app.test_client(), "session-owner", "old-password-123").status_code == 200
    assert login(app.test_client(), "session-owner", "new-password-456").status_code == 302


def test_disabling_account_revokes_existing_session(tmp_path):
    app = security_app(tmp_path)
    store = app.extensions["fivebr_users"]
    user_id = store.create_user(
        "disable-owner",
        "disable-password-123",
        role="admin",
    )
    client = app.test_client()
    assert login(client, "disable-owner", "disable-password-123").status_code == 302
    assert client.get("/").status_code == 200

    store.set_active(user_id, False)

    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_role_change_revokes_existing_session(tmp_path):
    app = security_app(tmp_path)
    store = app.extensions["fivebr_users"]
    user_id = store.create_user(
        "role-owner",
        "role-password-123",
        role="admin",
    )
    client = app.test_client()
    assert login(client, "role-owner", "role-password-123").status_code == 302
    assert client.get("/").status_code == 200

    store.set_role(user_id, "viewer")

    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    replacement = app.test_client()
    assert login(replacement, "role-owner", "role-password-123").status_code == 302
    assert replacement.get("/").status_code == 200


def test_inactive_user_cannot_login(tmp_path):
    app = security_app(tmp_path)
    store = app.extensions["fivebr_users"]
    user_id = store.create_user("inactive", "inactive-password-123", role="admin")
    with store.connect() as db:
        db.execute("UPDATE web_users SET active = 0 WHERE id = ?", (user_id,))
    assert login(app.test_client(), "inactive", "inactive-password-123").status_code == 200


def test_language_switch_rejects_external_next(tmp_path):
    app = security_app(tmp_path)
    response = app.test_client().get("/language/ar?next=//example.com/phish")
    assert response.status_code == 302
    assert not response.headers["Location"].startswith("//example.com")


def test_settings_reject_invalid_timezone_date_and_oversized_email(tmp_path):
    app = security_app(tmp_path)
    store = app.extensions["fivebr_users"]
    store.create_user("owner", "owner-password-123", role="admin")
    client = app.test_client()
    login(client, "owner", "owner-password-123")
    token = token_from(client.get("/settings"))
    response = client.post("/settings", data={
        "csrf_token": token, "language": "en", "theme": "auto",
        "timezone": "Mars/Olympus", "date_format": "executable-format",
        "email": "x" * 255,
    })
    assert response.status_code == 400


def test_username_validation(tmp_path):
    store = security_app(tmp_path).extensions["fivebr_users"]
    for username in ("", "ab", "contains spaces", "x" * 65):
        with pytest.raises(ValueError):
            store.create_user(username, "valid-password-123")


def test_session_lifetime_is_bounded(tmp_path):
    app = security_app(tmp_path)
    assert app.permanent_session_lifetime == timedelta(minutes=30)


def test_production_requires_secret_and_enables_secure_cookies(tmp_path, monkeypatch):
    monkeypatch.setenv("FIVEBR_ENV", "production")
    monkeypatch.setenv(
        "FIVEBR_TRUSTED_HOSTS",
        "filters.example.test",
    )
    monkeypatch.delenv("FIVEBR_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        create_app({"USER_DATABASE": tmp_path / "missing-secret.sqlite3"})
    monkeypatch.setenv("FIVEBR_SECRET_KEY", "stable-production-secret")
    app = create_app({"USER_DATABASE": tmp_path / "production.sqlite3"})
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["REMEMBER_COOKIE_SECURE"] is True
