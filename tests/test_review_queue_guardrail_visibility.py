from __future__ import annotations

import csv
from pathlib import Path

from scripts.services import (
    suggestions_service as service,
)

from web.app import create_app


def write_suggestion(
    path: Path,
    *,
    policy: str,
) -> None:
    fieldnames = [
        "Domain",
        "Seen",
        "Root",
        "Suggested Vendor",
        "Suggested Category",
        "Suggested Filter",
        "Confidence",
        "Recommendation",
        "Blocking Policy",
        "Blocking Policy Reason",
        "Blocking Policy Source",
        "Reasons",
    ]

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerow(
            {
                "Domain": "example.test",
                "Seen": "5",
                "Root": "example.test",
                "Suggested Vendor": "Example",
                "Suggested Category": "Streaming",
                "Suggested Filter": "streaming",
                "Confidence": "85",
                "Recommendation": "review",
                "Blocking Policy": policy,
                "Blocking Policy Reason": (
                    "Policy reason."
                ),
                "Blocking Policy Source": (
                    "category-policy"
                ),
                "Reasons": "test evidence",
            }
        )


def configure_runtime(
    tmp_path: Path,
    monkeypatch,
    *,
    policy: str,
) -> None:
    suggestions = (
        tmp_path
        / "suggestions.csv"
    )

    decisions = (
        tmp_path
        / "suggestion-decisions.csv"
    )

    write_suggestion(
        suggestions,
        policy=policy,
    )

    monkeypatch.setattr(
        service,
        "get_suggestions_csv",
        lambda: suggestions,
    )

    monkeypatch.setattr(
        service,
        "get_decisions_csv",
        lambda: decisions,
    )


def test_review_queue_service_previews_do_not_block(
    tmp_path: Path,
    monkeypatch,
):
    configure_runtime(
        tmp_path,
        monkeypatch,
        policy="do-not-block",
    )

    rows = service.load_review_queue()

    assert len(rows) == 1

    row = rows[0]

    assert row["Guardrail Mode"] == "shadow"

    assert (
        row["Guardrail Requirement"]
        == "require-override"
    )

    assert (
        row["Guardrail Would Block"]
        == "true"
    )

    assert (
        row["Guardrail Allowed"]
        == "true"
    )


def test_review_queue_service_previews_safe_policy(
    tmp_path: Path,
    monkeypatch,
):
    configure_runtime(
        tmp_path,
        monkeypatch,
        policy="safe-to-block",
    )

    row = service.load_review_queue()[0]

    assert (
        row["Guardrail Requirement"]
        == "allow"
    )

    assert (
        row["Guardrail Would Block"]
        == "false"
    )


def test_review_queue_uses_recorded_guardrail_when_available(
    tmp_path: Path,
    monkeypatch,
):
    configure_runtime(
        tmp_path,
        monkeypatch,
        policy="do-not-block",
    )

    suggestion = service.find_suggestion(
        "example.test"
    )

    assert suggestion is not None

    service.append_decision(
        suggestion,
        "ignored",
        "recorded decision",
    )

    row = service.load_review_queue(
        include_decided=True,
    )[0]

    assert row["Review Status"] == "ignored"

    assert (
        row["Guardrail Requirement"]
        == "allow"
    )

    assert (
        row["Guardrail Would Block"]
        == "false"
    )


def test_review_queue_route_displays_shadow_guardrail():
    app = create_app()
    app.config["TESTING"] = True

    response = app.test_client().get(
        "/review-queue"
    )

    html = response.get_data(
        as_text=True
    )

    assert response.status_code == 200

    # The header is always rendered, even when
    # the current review queue contains no rows.
    assert "Guardrail Shadow" in html
