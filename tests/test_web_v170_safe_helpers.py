import web.app as webapp


def test_v170_safe_helpers_exist():
    assert webapp.normalize_unknown("Unknown") == ""
    assert webapp.normalize_unknown("unknown", "Needs selection") == "Needs selection"
    assert webapp.normalize_unknown("Google") == "Google"
    assert webapp.confidence_level(90) == "high"
    assert webapp.confidence_level(60) == "medium"
    assert webapp.confidence_level(10) == "low"
    assert webapp.recommendation_badge("review") == "warning"
    assert webapp.recommendation_badge("approved-candidate") == "success"


def test_v170_helpers_registered_in_jinja():
    app = webapp.app
    assert "normalize_unknown" in app.jinja_env.globals
    assert "confidence_level" in app.jinja_env.globals
    assert "recommendation_badge" in app.jinja_env.globals
    assert "explain_suggestion" in app.jinja_env.globals
