from web.app import app


def test_v170_stage3_review_queue_template_has_badges_and_explain():
    row = {
        "Domain": "example.test",
        "Seen": "10",
        "Root": "example.test",
        "Suggested Vendor": "Unknown",
        "Suggested Category": "Telemetry",
        "Suggested Filter": "telemetry",
        "Confidence": "65",
        "Recommendation": "review",
        "Reasons": "matched test; confidence test",
    }
    with app.test_request_context("/review-queue"):
        html = app.jinja_env.get_template("review_queue.html").render(
            t=lambda key: key,
            current_lang="en",
            html_dir="ltr",
            other_lang="ar",
            rows=[row],
            stats={},
            vendors=[],
            categories=[],
            filters=[],
        )
    assert "total_suggestions" in html
    assert "needs_review" in html
    assert "65 / 100" in html
    assert "analyzer_explanation" in html
    assert "needs_selection" in html
