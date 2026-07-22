from scripts.services.root_cause_remediation import (
    build_remediation_preview,
    build_remediation_proposal,
    build_remediation_report,
)


def attribution(
    *,
    domain: str,
    root_cause: str,
    category: str,
    actual_filter: str,
    expected_filter: str,
    sources: list[str],
    conflict: bool = False,
    ambiguous: bool = False,
    severity: str = "medium",
):
    return {
        "domain": domain,
        "root_cause": root_cause,
        "category": category,
        "actual_filter": actual_filter,
        "expected_filter": expected_filter,
        "severity": severity,
        "filter_sources": sources,
        "filter_score": 30,
        "conflict": conflict,
        "ambiguous": ambiguous,
        "requires_review": True,
    }


def test_safe_preview_for_isolated_legacy_mapping():
    proposal = build_remediation_proposal(
        attribution(
            domain="www.gstatic.com",
            root_cause=(
                "legacy-mapping-leakage"
            ),
            category="Connectivity",
            actual_filter="privacy",
            expected_filter="connectivity",
            sources=["rule"],
        )
    )

    assert (
        proposal.action
        == "safe-preview-correction"
    )
    assert proposal.proposed_filter == (
        "connectivity"
    )
    assert proposal.automatic_candidate
    assert not proposal.requires_review
    assert proposal.proposes_change
    assert not proposal.production_changed


def test_direct_evidence_is_preserved_for_review():
    proposal = build_remediation_proposal(
        attribution(
            domain="youtubei.googleapis.com",
            root_cause=(
                "direct-evidence-conflict"
            ),
            category="Streaming",
            actual_filter="telemetry",
            expected_filter="streaming",
            sources=["database"],
            conflict=True,
            severity="high",
        )
    )

    assert (
        proposal.action
        == "preserve-and-review"
    )
    assert (
        proposal.proposed_filter
        == "telemetry"
    )
    assert not proposal.automatic_candidate
    assert proposal.requires_review
    assert not proposal.proposes_change


def test_ambiguous_resolution_is_not_corrected():
    proposal = build_remediation_proposal(
        attribution(
            domain="adservetx.media.net",
            root_cause=(
                "ambiguous-resolution"
            ),
            category="Streaming",
            actual_filter="social",
            expected_filter="streaming",
            sources=["rule"],
            conflict=True,
            ambiguous=True,
            severity="critical",
        )
    )

    assert (
        proposal.action
        == "preserve-and-review"
    )
    assert proposal.requires_review
    assert not proposal.automatic_candidate
    assert proposal.proposed_filter == "social"


def test_taxonomy_collision_is_deferred():
    proposal = build_remediation_proposal(
        attribution(
            domain="metrics2.data.hicloud.com",
            root_cause=(
                "possible-taxonomy-dimension-collision"
            ),
            category="Telemetry",
            actual_filter="mobile",
            expected_filter="telemetry",
            sources=["database"],
            conflict=True,
            severity="high",
        )
    )

    assert (
        proposal.action
        == "taxonomy-review"
    )
    assert proposal.requires_review
    assert not proposal.proposes_change


def test_summary_and_report():
    summary = build_remediation_preview(
        [
            attribution(
                domain="legacy.example",
                root_cause=(
                    "legacy-mapping-leakage"
                ),
                category="Streaming",
                actual_filter="social",
                expected_filter="streaming",
                sources=["rule"],
            ),
            attribution(
                domain="direct.example",
                root_cause=(
                    "direct-evidence-conflict"
                ),
                category="Streaming",
                actual_filter="telemetry",
                expected_filter="streaming",
                sources=["database"],
                conflict=True,
                severity="high",
            ),
            attribution(
                domain="taxonomy.example",
                root_cause=(
                    "possible-taxonomy-dimension-collision"
                ),
                category="Telemetry",
                actual_filter="mobile",
                expected_filter="telemetry",
                sources=["database"],
            ),
        ]
    )

    assert summary.domains_inspected == 3
    assert summary.proposals_created == 3
    assert summary.automatic_candidates == 1
    assert summary.requiring_review == 2
    assert summary.proposed_changes == 1
    assert summary.production_changes == 0

    assert summary.action_counts[
        "safe-preview-correction"
    ] == 1

    assert summary.action_counts[
        "preserve-and-review"
    ] == 1

    assert summary.action_counts[
        "taxonomy-review"
    ] == 1

    report = build_remediation_report(
        summary
    )

    assert (
        "5ibr Root-Cause Remediation Preview"
        in report
    )
    assert "legacy.example" in report
    assert "direct.example" in report
    assert "taxonomy.example" in report
    assert "Production changes     : 0" in report
