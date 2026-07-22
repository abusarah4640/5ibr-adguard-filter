from scripts.services.evidence_quality import (
    EvidenceQuality,
)
from scripts.services.unified_evidence import (
    make_unified_evidence,
)
from scripts.services.unified_evidence_collector import (
    UnifiedEvidenceBundle,
)
from scripts.services.unified_evidence_resolver import (
    candidate_has_direct_evidence,
    is_derived_filter_evidence,
    resolve_evidence_field,
)


def make_filter_evidence(
    *,
    source: str,
    value: str,
    score: int,
    derived: bool = False,
):
    metadata = {}

    if derived:
        metadata = {
            "derived_from": "category",
            "derived_category": "Social",
        }

    return make_unified_evidence(
        source=source,
        field="filter",
        value=value,
        quality=(
            EvidenceQuality.MODERATE
            if derived
            else EvidenceQuality.STRONG
        ),
        score=score,
        reason=f"{source} supports {value}",
        metadata=metadata,
    )


def test_category_derived_filter_is_detected():
    derived = make_filter_evidence(
        source="rule",
        value="social",
        score=30,
        derived=True,
    )

    direct = make_filter_evidence(
        source="database",
        value="streaming",
        score=20,
    )

    assert is_derived_filter_evidence(derived)
    assert not is_derived_filter_evidence(direct)


def test_direct_filter_outranks_higher_derived_filter():
    bundle = UnifiedEvidenceBundle(
        domain="nrdp.nccp.netflix.com",
        evidence=[
            make_filter_evidence(
                source="rule",
                value="social",
                score=30,
                derived=True,
            ),
            make_filter_evidence(
                source="database",
                value="streaming",
                score=20,
            ),
        ],
    )

    result = resolve_evidence_field(
        bundle,
        "filter",
    )

    assert result is not None
    assert result.value == "streaming"
    assert result.score == 20
    assert result.sources == (
        "database",
    )

    assert result.has_conflict
    assert len(result.competing) == 1
    assert result.competing[0].value == "social"
    assert result.competing[0].score == 30

    assert candidate_has_direct_evidence(
        result.competing[0]
    ) is False


def test_derived_filters_still_compete_when_no_direct_evidence():
    bundle = UnifiedEvidenceBundle(
        domain="example.test",
        evidence=[
            make_filter_evidence(
                source="rule",
                value="telemetry",
                score=30,
                derived=True,
            ),
            make_filter_evidence(
                source="rule",
                value="social",
                score=20,
                derived=True,
            ),
        ],
    )

    result = resolve_evidence_field(
        bundle,
        "filter",
    )

    assert result is not None
    assert result.value == "telemetry"
    assert result.score == 30
    assert result.has_conflict
