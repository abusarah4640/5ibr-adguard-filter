from web.i18n import TRANSLATIONS

from web.app import (
    confidence_level,
    create_app,
    explain_suggestion,
    normalize_unknown,
    recommendation_badge,
)


SAMPLE_ROW = {
    "Domain": "youtubei.googleapis.com",
    "Seen": "12",
    "Root": "googleapis.com",
    "Suggested Vendor": "Google",
    "Suggested Category": "Streaming",
    "Suggested Filter": "streaming",
    "Confidence": "85",
    "Recommendation": "review",
    "Blocking Policy": "do-not-block",
    "Blocking Policy Reason": (
        "Streaming endpoints may be required "
        "for playback, discovery or session control."
    ),
    "Blocking Policy Source": "category-policy",
    "Reasons": (
        "matched category keyword: youtube"
    ),
}


def make_app():
    app = create_app()
    app.config["TESTING"] = True
    return app


def render_template(
    template_name: str,
    rows: list[dict],
) -> str:
    app = make_app()

    with app.test_request_context("/"):
        return app.jinja_env.get_template(
            template_name
        ).render(
            rows=rows,
            t=lambda key: TRANSLATIONS["en"].get(key, key),
            normalize_unknown=normalize_unknown,
            confidence_level=confidence_level,
            recommendation_badge=(
                recommendation_badge
            ),
            explain_suggestion=explain_suggestion,
        )


def test_suggestions_shows_blocking_policy():
    html = render_template(
        "suggestions.html",
        [SAMPLE_ROW],
    )

    required = (
        "Blocking Policy",
        "do-not-block",
        "Streaming endpoints may be required",
        "category-policy",
        "text-bg-success",
    )

    for value in required:
        assert value in html


def test_review_queue_shows_blocking_policy():
    html = render_template(
        "review_queue.html",
        [SAMPLE_ROW],
    )

    required = (
        "Blocking Policy",
        "Do not block",
        "Blocking Policy Reason",
        "Blocking Policy Source",
        "category-policy",
        "text-bg-success",
    )

    for value in required:
        assert value in html


def test_suggestions_supports_legacy_rows():
    legacy = {
        key: value
        for key, value in SAMPLE_ROW.items()
        if not key.startswith(
            "Blocking Policy"
        )
    }

    html = render_template(
        "suggestions.html",
        [legacy],
    )

    assert "unknown" in html
    assert "text-bg-secondary" in html


def test_review_queue_supports_legacy_rows():
    legacy = {
        key: value
        for key, value in SAMPLE_ROW.items()
        if not key.startswith(
            "Blocking Policy"
        )
    }

    html = render_template(
        "review_queue.html",
        [legacy],
    )

    assert "unknown" in html
    assert "text-bg-secondary" in html


def test_real_routes_load_policy_headers():
    app = make_app()
    client = app.test_client()

    for path in (
        "/reports/suggestions",
        "/review-queue",
    ):
        response = client.get(path)

        assert response.status_code == 200
        assert (
            "Blocking Policy"
            in response.get_data(
                as_text=True
            )
        )
