from scripts.services.canonical_evidence_identity import (
    preferred_evidence_label,
)
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
    resolve_evidence_field,
)


def make_evidence(
    *,
    source: str,
    field: str,
    value: str,
    score: int,
):
    return make_unified_evidence(
        source=source,
        field=field,
        value=value,
        quality=EvidenceQuality.STRONG,
        score=score,
        reason=f"{source} supports {value}",
    )


def test_sony_preferred_vendor_label():
    assert (
        preferred_evidence_label(
            "vendor",
            "sony-playstation",
            "Sony",
        )
        == "Sony PlayStation"
    )


def test_meta_preferred_vendor_label():
    assert (
        preferred_evidence_label(
            "vendor",
            "meta",
            "Facebook",
        )
        == "Meta"
    )


def test_unknown_identity_preserves_fallback():
    assert (
        preferred_evidence_label(
            "vendor",
            "example-company",
            "Example Company",
        )
        == "Example Company"
    )


def test_resolver_uses_preferred_vendor_label():
    bundle = UnifiedEvidenceBundle(
        domain="event.api.playstation.net",
        evidence=[
            make_evidence(
                source="rule",
                field="vendor",
                value="Sony",
                score=35,
            ),
            make_evidence(
                source="knowledge",
                field="vendor",
                value="Sony PlayStation",
                score=50,
            ),
            make_evidence(
                source="database",
                field="vendor",
                value="PlayStation",
                score=20,
            ),
        ],
    )

    result = resolve_evidence_field(
        bundle,
        "vendor",
    )

    assert result is not None
    assert result.identity == "sony-playstation"
    assert result.value == "Sony PlayStation"
    assert result.score == 100
    assert result.sources == (
        "database",
        "knowledge",
        "rule",
    )


def test_non_vendor_field_keeps_strongest_display_value():
    bundle = UnifiedEvidenceBundle(
        domain="example.test",
        evidence=[
            make_evidence(
                source="knowledge",
                field="category",
                value="Smart TV",
                score=50,
            ),
            make_evidence(
                source="database",
                field="category",
                value="smart-tv",
                score=20,
            ),
        ],
    )

    result = resolve_evidence_field(
        bundle,
        "category",
    )

    assert result is not None
    assert result.identity == "smart tv"
    assert result.value == "Smart TV"
