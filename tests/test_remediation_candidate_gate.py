from scripts.services.remediation_candidate_gate import (
    base_safety_requirements,
    build_candidate_gate_report,
    domain_family,
    run_candidate_safety_gate,
)


def proposal(
    *,
    domain: str,
    category: str = "Streaming",
    current_filter: str = "social",
    proposed_filter: str = "streaming",
    automatic: bool = True,
    conflict: bool = False,
    ambiguous: bool = False,
    sources: list[str] | None = None,
):
    return {
        "domain": domain,
        "root_cause": "legacy-mapping-leakage",
        "action": "safe-preview-correction",
        "current": {
            "category": category,
            "filter": current_filter,
        },
        "proposed": {
            "category": category,
            "filter": proposed_filter,
        },
        "automatic_candidate": automatic,
        "requires_review": False,
        "proposes_change": True,
        "production_changed": False,
        "metadata": {
            "filter_sources": (
                sources
                if sources is not None
                else ["rule"]
            ),
            "filter_score": 30,
            "conflict": conflict,
            "ambiguous": ambiguous,
        },
    }


def test_domain_family():
    assert (
        domain_family("api.example.com")
        == "example.com"
    )

    assert (
        domain_family("example.com")
        == "example.com"
    )


def test_family_with_three_consistent_candidates_is_eligible():
    summary = run_candidate_safety_gate(
        [
            proposal(
                domain="a.example.com",
            ),
            proposal(
                domain="b.example.com",
            ),
            proposal(
                domain="c.example.com",
            ),
        ],
        minimum_family_support=3,
    )

    assert summary.eligible == 3
    assert summary.held == 0
    assert summary.rejected == 0
    assert summary.production_changes == 0

    assert all(
        result.eligible
        for result in summary.results
    )


def test_small_family_is_held_for_review():
    summary = run_candidate_safety_gate(
        [
            proposal(
                domain="a.example.com",
            ),
            proposal(
                domain="b.example.com",
            ),
        ],
        minimum_family_support=3,
    )

    assert summary.eligible == 0
    assert summary.held == 2
    assert summary.rejected == 0


def test_inconsistent_family_is_held():
    summary = run_candidate_safety_gate(
        [
            proposal(
                domain="a.example.com",
                proposed_filter="streaming",
            ),
            proposal(
                domain="b.example.com",
                proposed_filter="ads",
            ),
            proposal(
                domain="c.example.com",
                proposed_filter="streaming",
            ),
        ],
        minimum_family_support=2,
    )

    assert summary.eligible == 0
    assert summary.held == 3


def test_invalid_candidate_is_rejected_when_all_are_inspected():
    invalid = proposal(
        domain="bad.example.com",
        conflict=True,
    )

    passed, reasons = (
        base_safety_requirements(
            invalid
        )
    )

    assert not passed
    assert reasons

    summary = run_candidate_safety_gate(
        [invalid],
        minimum_family_support=1,
        automatic_only=False,
    )

    assert summary.rejected == 1
    assert summary.production_changes == 0


def test_report():
    summary = run_candidate_safety_gate(
        [
            proposal(
                domain="a.example.com",
            ),
            proposal(
                domain="b.example.com",
            ),
            proposal(
                domain="c.example.com",
            ),
        ],
        minimum_family_support=3,
    )

    report = build_candidate_gate_report(
        summary
    )

    assert (
        "5ibr Remediation Candidate Safety Gate"
        in report
    )
    assert (
        "eligible-for-controlled-promotion"
        in report
    )
    assert "Production changes            : 0" in report
