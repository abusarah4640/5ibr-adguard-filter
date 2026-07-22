from pathlib import Path

from web.app import create_app
from web.app import confidence_level, explain_suggestion, normalize_unknown, recommendation_badge


def make_app(tmp_path: Path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "USER_DATABASE": tmp_path / "users.sqlite3",
    })


def test_language_priority_url_cookie_session_browser_default(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    with client.session_transaction() as state:
        state["language"] = "ar"
    client.set_cookie("fivebr_lang", "en")
    assert 'lang="ar"' in client.get("/?lang=ar", headers={"Accept-Language": "en"}).get_data(as_text=True)
    assert 'lang="en"' in client.get("/", headers={"Accept-Language": "ar"}).get_data(as_text=True)


def test_browser_language_and_direction_are_used_without_preferences(tmp_path):
    app = make_app(tmp_path)
    response = app.test_client().get("/", headers={"Accept-Language": "ar-SA,ar;q=0.9"})
    body = response.get_data(as_text=True)
    assert 'lang="ar"' in body
    assert 'dir="rtl"' in body


def test_hashed_login_remember_logout_and_settings(tmp_path):
    app = make_app(tmp_path)
    store = app.extensions["fivebr_users"]
    user_id = store.create_user("owner", "correct-horse-battery", role="admin")
    with store.connect() as db:
        password_hash = db.execute("SELECT password_hash FROM web_users WHERE id = ?", (user_id,)).fetchone()[0]
    assert "correct-horse-battery" not in password_hash

    client = app.test_client()
    response = client.post("/login", data={"username": "owner", "password": "correct-horse-battery", "remember": "on"})
    assert response.status_code == 302
    assert "fivebr_remember=" in response.headers.get("Set-Cookie", "")
    response = client.post("/settings", data={
        "display_name": "Owner", "email": "owner@example.test", "language": "ar",
        "theme": "dark", "timezone": "Asia/Riyadh", "date_format": "dd/mm/yyyy",
    })
    assert response.status_code == 302
    saved = store.get(user_id)
    assert (saved.language, saved.theme, saved.timezone) == ("ar", "dark", "Asia/Riyadh")
    assert client.post("/logout").status_code == 302


def test_mutating_routes_require_authentication(tmp_path):
    app = create_app({
        "TESTING": True, "SECURITY_TESTING": True, "CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret", "USER_DATABASE": tmp_path / "users.sqlite3",
    })
    app.extensions["fivebr_users"].create_user("owner", "correct-horse-battery", role="admin")
    response = app.test_client().post("/actions/validate")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_every_factory_app_registers_analyzer_ux_helpers(tmp_path):
    app = make_app(tmp_path)
    expected = {
        "normalize_unknown": normalize_unknown,
        "confidence_level": confidence_level,
        "recommendation_badge": recommendation_badge,
        "explain_suggestion": explain_suggestion,
    }
    for name, helper in expected.items():
        assert app.jinja_env.globals[name] is helper

    template = app.jinja_env.from_string(
        "{{ normalize_unknown('Unknown', 'fallback') }}|"
        "{{ confidence_level(75) }}|{{ recommendation_badge('review') }}|"
        "{{ explain_suggestion({'Reasons': 'one; two'})|join(',') }}"
    )
    assert template.render() == "fallback|medium|warning|one,two"
