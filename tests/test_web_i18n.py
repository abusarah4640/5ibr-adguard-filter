
from web.app import create_app


def test_arabic_language_cookie_renders_rtl_dashboard():
    app = create_app()
    app.testing = True
    client = app.test_client()
    client.set_cookie("fivebr_lang", "ar")
    response = client.get("/")
    assert response.status_code == 200
    body = response.data.decode("utf-8")
    assert 'dir="rtl"' in body
    assert "لوحة التحكم" in body


def test_language_switch_sets_cookie():
    app = create_app()
    app.testing = True
    client = app.test_client()
    response = client.get("/language/ar")
    assert response.status_code in {302, 303}
    assert "fivebr_lang=ar" in response.headers.get("Set-Cookie", "")


def test_arabic_dashboard_translates_readiness_ui(monkeypatch):
    import web.app as web_app

    class Summary:
        guardrail_coverage_rate = 0.0
        classified_approval_attempts = 0
        unclassified_approval_attempts = 0
        shadow_rows = 0
        enforce_rows = 0

    class Progress:
        percent = 0.0
        passed_checks = 0
        total_checks = 6
        classified_approvals_remaining = 100
        coverage_gap = 95.0
        unclassified_approvals_excess = 0
        classified_block_rate_excess = 0.0
        shadow_rows_remaining = 1
        enforce_rows_excess = 0

    class Readiness:
        ready = False
        status = "not-ready"
        reasons = ()
        diagnostics = ()
        summary = Summary()
        progress = Progress()

    monkeypatch.setattr(web_app, "load_enforcement_readiness", lambda: Readiness())
    app = create_app()
    app.testing = True
    client = app.test_client()
    client.set_cookie("fivebr_lang", "ar")
    response = client.get("/")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "جاهزية ضوابط الحماية" in body
    assert "التقدم نحو الجاهزية" in body
    assert "تشخيص الجاهزية" in body
    assert "للعرض فقط" in body
    assert "Guardrail Readiness" not in body
