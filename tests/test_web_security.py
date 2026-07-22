import re
from datetime import timedelta

import pytest

from web.app import create_app


def security_app(tmp_path, **config):
    values = {
        "TESTING": True,
        "SECURITY_TESTING": True,
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
    monkeypatch.delenv("FIVEBR_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        create_app({"USER_DATABASE": tmp_path / "missing-secret.sqlite3"})
    monkeypatch.setenv("FIVEBR_SECRET_KEY", "stable-production-secret")
    app = create_app({"USER_DATABASE": tmp_path / "production.sqlite3"})
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["REMEMBER_COOKIE_SECURE"] is True
