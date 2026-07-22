import re

from web.app import create_app


def app_for(tmp_path):
    return create_app({
        "TESTING": True,
        "INSECURE_TEST_BYPASS": True,
        "SECRET_KEY": "ui-polish-test-secret",
        "USER_DATABASE": tmp_path / "ui-users.sqlite3",
    })


def test_theme_assets_and_bootstrap_icons_are_loaded(tmp_path):
    body = app_for(tmp_path).test_client().get("/").get_data(as_text=True)
    assert "bootstrap@5.3.3" in body
    assert "bootstrap-icons@1.11.3" in body
    assert "/static/css/theme.css" in body
    assert "/static/css/components.css" in body
    assert "/static/js/app.js" in body
    assert "data-theme-toggle" in body


def test_every_rendered_post_form_contains_csrf_token(tmp_path):
    app = app_for(tmp_path)
    client = app.test_client()
    for path in ("/", "/intelligence", "/releases", "/login"):
        body = client.get(path).get_data(as_text=True)
        forms = re.findall(r"<form\b[^>]*method=[\"']post[\"'][^>]*>(.*?)</form>", body, re.I | re.S)
        assert all('name="csrf_token"' in form for form in forms), path


def test_arabic_intelligence_has_no_known_english_diagnostic_messages(tmp_path):
    app = app_for(tmp_path)
    body = app.test_client().get("/intelligence?lang=ar").get_data(as_text=True)
    forbidden = (
        "knowledge entries loaded", "vendor groups loaded", "category groups loaded",
        "filter mappings loaded", "decision construction", "reason generation operational",
        "explanation creation operational", "Please log in to access this page",
    )
    assert 'dir="rtl"' in body
    assert not any(message in body for message in forbidden)


def test_arabic_csrf_message_is_actionable(tmp_path):
    app = create_app({
        "TESTING": True, "INSECURE_TEST_BYPASS": False,
        "SECRET_KEY": "csrf-ui-secret", "USER_DATABASE": tmp_path / "csrf-ui.sqlite3",
    })
    store = app.extensions["fivebr_users"]
    store.create_user("arabic-admin", "arabic-admin-password", role="admin")
    client = app.test_client()
    token = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/login").get_data(as_text=True)).group(1)
    client.post("/login?lang=ar", data={"csrf_token": token, "username": "arabic-admin", "password": "arabic-admin-password"})
    response = client.post("/actions/intelligence-check?lang=ar")
    assert response.status_code == 400
    body = response.get_data(as_text=True)
    assert "انتهت صلاحية الجلسة" in body
    assert "حدّث الصفحة" in body


def test_arabic_unauthorized_message_is_localized(tmp_path):
    app = create_app({
        "TESTING": True, "INSECURE_TEST_BYPASS": False, "CSRF_ENABLED": False,
        "SECRET_KEY": "auth-ui-secret", "USER_DATABASE": tmp_path / "auth-ui.sqlite3",
    })
    client = app.test_client()
    response = client.get("/domains/add?lang=ar", follow_redirects=True)
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "يرجى تسجيل الدخول للمتابعة" in body
    assert "Please log in" not in body


def test_rc_styles_include_responsive_rtl_table_and_loading_states(tmp_path):
    client = app_for(tmp_path).test_client()
    theme = client.get("/static/css/theme.css").get_data(as_text=True)
    components = client.get("/static/css/components.css").get_data(as_text=True)
    script = client.get("/static/js/app.js").get_data(as_text=True)
    assert '[dir="rtl"]' in theme
    assert "position: sticky" in components
    assert ".empty-state" in components
    assert ".skeleton" in components
    assert ".btn.is-loading" in components
    assert "localStorage" in script
    assert "bootstrap.Toast" in script
