from web.app import app
from web.i18n import TRANSLATIONS


def test_v170_stage2_suggestion_form_template_uses_ux_helpers():
    row = {
        "Domain": "unknown.example.test",
        "Seen": "5",
        "Root": "example.test",
        "Suggested Vendor": "Unknown",
        "Suggested Category": "Unknown",
        "Suggested Filter": "unknown",
        "Confidence": "0",
        "Recommendation": "unknown",
        "Reasons": "no local analyzer rules matched",
    }

    with app.test_request_context("/suggestions/unknown.example.test/approve"):
        html = app.jinja_env.get_template("suggestion_form.html").render(
            t=lambda key: TRANSLATIONS["en"].get(key, key),
            current_lang="en",
            html_dir="ltr",
            other_lang="ar",
            row=row,
            suggestion=row,
            vendors=["Example"],
            categories=["Telemetry"],
            filters=["telemetry"],
        )

    assert "Needs selection" in html
    assert "0 / 100" in html
    assert "Analyzer Explanation" in html
