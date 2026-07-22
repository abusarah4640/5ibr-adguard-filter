import re

from web.app import create_app


def make_app(tmp_path):
    return create_app({
        "TESTING": True,
        "INSECURE_TEST_BYPASS": False,
        "SECRET_KEY": "v201-auth-ux-secret",
        "USER_DATABASE": tmp_path / "v201-users.sqlite3",
    })


def csrf(body: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', body)
    assert match
    return match.group(1)


def login(client, username: str, password: str):
    token = csrf(client.get("/login").get_data(as_text=True))
    return client.post("/login", data={
        "csrf_token": token, "username": username, "password": password,
    })



def test_guest_sensitive_pages_redirect_to_login(tmp_path):
    client = make_app(tmp_path).test_client()
    for path in ("/", "/domains", "/releases", "/review-queue"):
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].startswith("/login?next=")


def test_admin_editor_viewer_see_only_permitted_controls(tmp_path):
    app = make_app(tmp_path)
    store = app.extensions["fivebr_users"]
    store.create_user("admin-user", "admin-password-123", role="admin", display_name="Release Admin")
    store.create_user("editor-user", "editor-password-123", role="editor")
    store.create_user("viewer-user", "viewer-password-123", role="viewer")

    admin = app.test_client()
    login(admin, "admin-user", "admin-password-123")
    admin_home = admin.get("/").get_data(as_text=True)
    admin_domains = admin.get("/domains").get_data(as_text=True)
    assert "Release Admin" in admin_home and 'action="/logout"' in admin_home
    assert 'href="/domains/add"' in admin_domains
    assert 'action="/actions/build"' in admin_home

    editor = app.test_client()
    login(editor, "editor-user", "editor-password-123")
    editor_home = editor.get("/").get_data(as_text=True)
    editor_domains = editor.get("/domains").get_data(as_text=True)
    assert "editor-user" in editor_home
    assert 'href="/domains/add"' in editor_domains
    assert 'action="/actions/build"' not in editor_home
    assert "/delete" not in editor_domains

    viewer = app.test_client()
    login(viewer, "viewer-user", "viewer-password-123")
    viewer_home = viewer.get("/").get_data(as_text=True)
    viewer_domains = viewer.get("/domains").get_data(as_text=True)
    assert "viewer-user" in viewer_home and 'action="/logout"' in viewer_home
    assert 'href="/domains/add"' not in viewer_domains
    assert "/edit" not in viewer_domains and "/delete" not in viewer_domains
    assert 'action="/actions/build"' not in viewer_home


def test_logout_is_post_only_and_csrf_protected(tmp_path):
    app = make_app(tmp_path)
    app.extensions["fivebr_users"].create_user("logout-user", "logout-password-123", role="viewer")
    client = app.test_client()
    login(client, "logout-user", "logout-password-123")
    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 400
    body = client.get("/").get_data(as_text=True)
    assert client.post("/logout", data={"csrf_token": csrf(body)}).status_code == 302


def test_guest_sensitive_post_redirects_safely_without_execution(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    called = []
    monkeypatch.setattr("web.app.run_fivebr", lambda *args: called.append(args) or (0, "ok"))
    client = app.test_client()
    response = client.post(
        "/actions/build",
        headers={"Referer": "http://localhost/releases"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?next=/releases")
    assert called == []

    external = client.post(
        "/actions/build",
        headers={"Referer": "https://evil.example/phish"},
    )
    assert "evil.example" not in external.headers["Location"]


def test_logged_in_missing_csrf_gets_session_expiry_message(tmp_path):
    app = make_app(tmp_path)
    app.extensions["fivebr_users"].create_user("csrf-user", "csrf-password-123", role="admin")
    client = app.test_client()
    login(client, "csrf-user", "csrf-password-123")
    response = client.post("/actions/validate?lang=ar")
    assert response.status_code == 400
    body = response.get_data(as_text=True)
    assert "انتهت صلاحية الجلسة" in body


def test_targeted_policy_phrases_are_localized_in_arabic(tmp_path):
    app = make_app(tmp_path)
    with app.test_request_context("/?lang=ar"):
        helper = app.jinja_env.globals["translate_dynamic_text"]
        for phrase in (
            "Unknown blocking policy requires manual review before a decision",
            "requires manual review confirmation",
            "undocumented reason",
            "no known policy",
        ):
            translated = helper(phrase)
            assert translated != phrase
            assert not re.search(r"[A-Za-z]{3,}", translated)
