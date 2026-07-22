from web.app import app


def test_v170_stage4_analysis_template_uses_badges_and_explain():
    row = {
        "Domain": "beacons2.gvt2.com",
        "Seen": "10",
        "Root": "gvt2.com",
        "Suggested Vendor": "Google",
        "Suggested Category": "Telemetry",
        "Suggested Filter": "telemetry",
        "Confidence": "65",
        "Recommendation": "review",
        "Reasons": "matched vendor; matched telemetry keyword",
    }

    with app.test_request_context("/analysis"):
        html = app.jinja_env.get_template("analysis.html").render(
            t=lambda key: {"explain": "Explain"}.get(key, key),
            rows=[row],
            stats={
                "total": 1,
                "review": 1,
                "unknown": 0,
                "avg_confidence": 65,
                "high_confidence": 0,
            },
            vendors=["Google"],
            categories=["Telemetry"],
            recommendations=["review"],
            top_vendors=[("Google", 1)],
            top_categories=[("Telemetry", 1)],
            top_filters=[("telemetry", 1)],
            top_recommendations=[("review", 1)],
        )

    assert "65 / 100" in html
    assert "Explain" in html
    assert "matched vendor" in html
    assert "bg-warning" in html
