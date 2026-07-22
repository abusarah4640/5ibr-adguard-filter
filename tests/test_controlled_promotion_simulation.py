import json

from scripts.services.controlled_promotion_simulation import (
    apply_mapping_updates,
    build_mapping_updates,
    changed_fields,
    eligible_gate_results,
    SimulatedDecision,
)


def gate_result(
    *,
    domain: str,
    category: str,
    proposed_filter: str,
    eligible: bool = True,
):
    return {
        "domain": domain,
        "eligible": eligible,
        "decision": (
            "eligible-for-controlled-promotion"
            if eligible
            else "hold-for-review"
        ),
        "current": {
            "category": category,
            "filter": "legacy",
        },
        "proposed_filter": proposed_filter,
    }


def test_eligible_gate_results():
    payload = {
        "results": [
            gate_result(
                domain="a.example",
                category="Streaming",
                proposed_filter="streaming",
            ),
            gate_result(
                domain="b.example",
                category="Streaming",
                proposed_filter="streaming",
                eligible=False,
            ),
        ]
    }

    rows = eligible_gate_results(payload)

    assert len(rows) == 1
    assert rows[0]["domain"] == "a.example"


def test_build_mapping_updates_deduplicates_categories():
    updates = build_mapping_updates(
        [
            gate_result(
                domain="a.example",
                category="Streaming",
                proposed_filter="streaming",
            ),
            gate_result(
                domain="b.example",
                category="Streaming",
                proposed_filter="streaming",
            ),
            gate_result(
                domain="c.example",
                category="Connectivity",
                proposed_filter="connectivity",
            ),
        ]
    )

    assert updates == {
        "Streaming": "streaming",
        "Connectivity": "connectivity",
    }


def test_conflicting_mapping_updates_are_rejected():
    try:
        build_mapping_updates(
            [
                gate_result(
                    domain="a.example",
                    category="Streaming",
                    proposed_filter="streaming",
                ),
                gate_result(
                    domain="b.example",
                    category="Streaming",
                    proposed_filter="social",
                ),
            ]
        )
    except ValueError as exc:
        assert (
            "conflicting promotion proposals"
            in str(exc)
        )
    else:
        raise AssertionError(
            "conflicting updates were accepted"
        )


def test_apply_mapping_updates_does_not_mutate_original():
    original = {
        "filter_map": {
            "Streaming": "social",
            "Connectivity": "privacy",
        }
    }

    simulated = apply_mapping_updates(
        original,
        {
            "Streaming": "streaming",
            "Connectivity": "connectivity",
        },
    )

    assert original["filter_map"] == {
        "Streaming": "social",
        "Connectivity": "privacy",
    }

    assert simulated["filter_map"] == {
        "Streaming": "streaming",
        "Connectivity": "connectivity",
    }


def test_changed_fields():
    before = SimulatedDecision(
        vendor="Example",
        category="Streaming",
        filter_name="social",
        confidence=60,
        recommendation="review",
    )

    after = SimulatedDecision(
        vendor="Example",
        category="Streaming",
        filter_name="streaming",
        confidence=60,
        recommendation="review",
    )

    assert changed_fields(
        before,
        after,
    ) == ("filter",)
