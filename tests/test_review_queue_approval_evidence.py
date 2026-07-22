from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import web.app as webapp

from scripts.services import (
    suggestions_service as service,
)

from web.app import (
    confidence_level,
    create_app,
    explain_suggestion,
    normalize_unknown,
    recommendation_badge,
)


def sample_suggestion(
    policy: str = "do-not-block",
) -> dict[str, str]:
    return {
        "Domain": "evidence.test",
        "Seen": "7",
        "Root": "evidence.test",
        "Suggested Vendor": "Example",
        "Suggested Category": "Streaming",
        "Suggested Filter": "streaming",
        "Confidence": "85",
        "Recommendation": "review",
        "Blocking Policy": policy,
        "Blocking Policy Reason": (
            "Policy test reason."
        ),
        "Blocking Policy Source": (
            "category-policy"
        ),
        "Reasons": "test evidence",
        "Guardrail Mode": "shadow",
        "Guardrail Requirement": (
            "require-override"
        ),
        "Guardrail Would Block": "true",
        "Guardrail Allowed": "true",
        "Guardrail Reason": (
            "Override required."
        ),
    }


def read_rows(
    path: Path,
) -> list[dict[str, str]]:
    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(
            csv.DictReader(file)
        )


def test_append_decision_records_approval_evidence(
    tmp_path: Path,
    monkeypatch,
):
    decisions = (
        tmp_path
        / "suggestion-decisions.csv"
    )

    monkeypatch.setattr(
        service,
        "get_decisions_csv",
        lambda: decisions,
    )

    service.append_decision(
        sample_suggestion(),
        "approved",
        "tested override",
        test_confirmed=True,
        override_confirmed=True,
        manual_review_confirmed=False,
    )

    row = read_rows(
        decisions
    )[0]

    assert row["Test Confirmed"] == "true"
    assert row["Override Confirmed"] == "true"

    assert (
        row["Manual Review Confirmed"]
        == "false"
    )

    assert (
        row["Guardrail Would Block"]
        == "false"
    )

    assert (
        row["Guardrail Allowed"]
        == "true"
    )


def test_missing_override_remains_shadow_violation(
    tmp_path: Path,
    monkeypatch,
):
    decisions = (
        tmp_path
        / "suggestion-decisions.csv"
    )

    monkeypatch.setattr(
        service,
        "get_decisions_csv",
        lambda: decisions,
    )

    service.append_decision(
        sample_suggestion(),
        "approved",
        "reason supplied",
        override_confirmed=False,
    )

    row = read_rows(
        decisions
    )[0]

    assert (
        row["Override Confirmed"]
        == "false"
    )

    assert (
        row["Guardrail Would Block"]
        == "true"
    )

    # Shadow mode still permits the action.
    assert (
        row["Guardrail Allowed"]
        == "true"
    )


def test_review_route_forwards_evidence_fields(
    monkeypatch,
):
    captured: dict = {}

    monkeypatch.setattr(
        webapp,
        "find_suggestion",
        lambda domain: sample_suggestion(),
    )

    monkeypatch.setattr(
        webapp,
        "add_validated_domain",
        lambda **kwargs: (True, []),
    )

    monkeypatch.setattr(
        webapp,
        "run_fivebr",
        lambda *args: (0, "build ok"),
    )

    monkeypatch.setattr(
        webapp,
        "remove_suggestion",
        lambda domain: None,
    )

    monkeypatch.setattr(
        webapp,
        "log_event",
        lambda *args: None,
    )

    def capture(
        row,
        action,
        reason="",
        actor="web-ui",
        **evidence,
    ):
        captured.update(
            {
                "action": action,
                "reason": reason,
                **evidence,
            }
        )

    monkeypatch.setattr(
        webapp,
        "append_decision",
        capture,
    )

    app = create_app()
    app.config["TESTING"] = True

    response = app.test_client().post(
        "/review-queue/evidence.test/approved",
        data={
            "reason": "manual evidence",
            "test_confirmed": "on",
            "override_confirmed": "on",
            "manual_review_confirmed": "on",
        },
    )

    assert response.status_code in {
        302,
        303,
    }

    assert captured["action"] == "approved"
    assert captured["reason"] == "manual evidence"
    assert captured["test_confirmed"] is True
    assert captured["override_confirmed"] is True

    assert (
        captured["manual_review_confirmed"]
        is True
    )


def test_review_route_defaults_missing_evidence_to_false(
    monkeypatch,
):
    captured: dict = {}

    monkeypatch.setattr(
        webapp,
        "find_suggestion",
        lambda domain: sample_suggestion(
            "safe-to-block"
        ),
    )

    monkeypatch.setattr(
        webapp,
        "add_validated_domain",
        lambda **kwargs: (True, []),
    )

    monkeypatch.setattr(
        webapp,
        "run_fivebr",
        lambda *args: (0, "build ok"),
    )

    monkeypatch.setattr(
        webapp,
        "remove_suggestion",
        lambda domain: None,
    )

    monkeypatch.setattr(
        webapp,
        "log_event",
        lambda *args: None,
    )

    def capture(
        row,
        action,
        reason="",
        actor="web-ui",
        **evidence,
    ):
        captured.update(evidence)

    monkeypatch.setattr(
        webapp,
        "append_decision",
        capture,
    )

    app = create_app()
    app.config["TESTING"] = True

    response = app.test_client().post(
        "/review-queue/evidence.test/approved",
    )

    assert response.status_code in {
        302,
        303,
    }

    assert captured["test_confirmed"] is False
    assert captured["override_confirmed"] is False

    assert (
        captured["manual_review_confirmed"]
        is False
    )


def test_template_renders_approval_evidence_fields():
    app = create_app()

    with app.test_request_context(
        "/review-queue"
    ):
        html = app.jinja_env.get_template(
            "review_queue.html"
            ).render(
                rows=[sample_suggestion()],
                current_user=SimpleNamespace(is_authenticated=True, role="admin", theme="auto"),
                csrf_token=lambda: "test-csrf-token",
            t=lambda key: key,
            normalize_unknown=normalize_unknown,
            confidence_level=confidence_level,
            recommendation_badge=(
                recommendation_badge
            ),
            explain_suggestion=explain_suggestion,
        )

    required = (
        'name="reason"',
        'name="test_confirmed"',
        'name="override_confirmed"',
        'name="manual_review_confirmed"',
        "shadow_mode_approval_note",
    )

    for value in required:
        assert value in html
