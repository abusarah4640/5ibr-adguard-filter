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
    EvidenceCandidate,
    ResolvedEvidenceField,
    UnifiedEvidenceResolution,
    resolve_evidence_field,
    resolve_unified_evidence,
)


def evidence(
    *,
    source: str,
    field: str,
    value: str,
    score: int,
    quality: EvidenceQuality,
):
    return make_unified_evidence(
        source=source,
        field=field,
        value=value,
        score=score,
        quality=quality,
        reason=f"{source} supports {value}",
    )


def make_playstation_bundle():
    return UnifiedEvidenceBundle(
        domain="event.api.np.km.playstation.net",
        evidence=[
            evidence(
                source="rule",
                field="vendor",
                value="Sony",
                score=35,
                quality=EvidenceQuality.STRONG,
            ),
            evidence(
                source="knowledge",
                field="vendor",
                value="Sony PlayStation",
                score=50,
                quality=EvidenceQuality.STRONG,
            ),
            evidence(
                source="database",
                field="vendor",
                value="Sony PlayStation",
                score=20,
                quality=EvidenceQuality.STRONG,
            ),
            evidence(
                source="rule",
                field="category",
                value="Telemetry",
                score=30,
                quality=EvidenceQuality.MODERATE,
            ),
            evidence(
                source="knowledge",
                field="category",
                value="Gaming",
                score=50,
                quality=EvidenceQuality.STRONG,
            ),
            evidence(
                source="database",
                field="category",
                value="Gaming",
                score=20,
                quality=EvidenceQuality.STRONG,
            ),
            evidence(
                source="knowledge",
                field="filter",
                value="gaming",
                score=50,
                quality=EvidenceQuality.STRONG,
            ),
            evidence(
                source="database",
                field="filter",
                value="gaming",
                score=20,
                quality=EvidenceQuality.STRONG,
            ),
        ],
    )


def test_resolver_combines_canonical_vendor_support():
    bundle = make_playstation_bundle()

    result = resolve_evidence_field(
        bundle,
        "vendor",
    )

    assert isinstance(
        result,
        ResolvedEvidenceField,
    )

    assert result.value == "Sony PlayStation"
    assert result.identity == "sony-playstation"
    assert result.score == 100
    assert result.sources == (
        "database",
        "knowledge",
        "rule",
    )
    assert not result.has_conflict
    assert not result.ambiguous


def test_resolver_selects_supported_category_winner():
    bundle = make_playstation_bundle()

    result = resolve_evidence_field(
        bundle,
        "category",
    )

    assert result is not None
    assert result.value == "Gaming"
    assert result.identity == "gaming"
    assert result.score == 70
    assert result.quality == EvidenceQuality.STRONG
    assert result.sources == (
        "database",
        "knowledge",
    )

    assert result.has_conflict
    assert len(result.competing) == 1
    assert result.competing[0].value == "Telemetry"
    assert result.competing[0].score == 30
    assert not result.ambiguous


def test_resolver_selects_filter_without_conflict():
    bundle = make_playstation_bundle()

    result = resolve_evidence_field(
        bundle,
        "filter",
    )

    assert result is not None
    assert result.value == "gaming"
    assert result.score == 70
    assert result.sources == (
        "database",
        "knowledge",
    )
    assert not result.has_conflict


def test_resolver_detects_ambiguous_tie():
    bundle = UnifiedEvidenceBundle(
        domain="ambiguous.example.test",
        evidence=[
            evidence(
                source="rule",
                field="category",
                value="Gaming",
                score=30,
                quality=EvidenceQuality.MODERATE,
            ),
            evidence(
                source="database",
                field="category",
                value="Telemetry",
                score=30,
                quality=EvidenceQuality.MODERATE,
            ),
        ],
    )

    result = resolve_evidence_field(
        bundle,
        "category",
    )

    assert result is not None
    assert result.ambiguous
    assert result.has_conflict
    assert len(result.competing) == 1


def test_resolution_tracks_unresolved_fields():
    bundle = UnifiedEvidenceBundle(
        domain="partial.example.test",
        evidence=[
            evidence(
                source="knowledge",
                field="vendor",
                value="Example",
                score=50,
                quality=EvidenceQuality.STRONG,
            )
        ],
    )

    resolution = resolve_unified_evidence(
        bundle
    )

    assert isinstance(
        resolution,
        UnifiedEvidenceResolution,
    )

    assert resolution.get("vendor") is not None
    assert resolution.get("category") is None
    assert resolution.get("filter") is None

    assert resolution.unresolved_fields == (
        "category",
        "filter",
    )


def test_resolution_serialization():
    bundle = make_playstation_bundle()
    resolution = resolve_unified_evidence(
        bundle
    )

    payload = resolution.to_dict()

    assert payload["domain"] == (
        "event.api.np.km.playstation.net"
    )
    assert payload["has_conflicts"] is True
    assert payload["has_ambiguity"] is False
    assert payload["unresolved_fields"] == []

    assert (
        payload["fields"]["vendor"]["value"]
        == "Sony PlayStation"
    )

    assert (
        payload["fields"]["category"]["value"]
        == "Gaming"
    )

    assert (
        payload["fields"]["category"][
            "competing_count"
        ]
        == 1
    )

    assert isinstance(
        resolution.get("vendor"),
        ResolvedEvidenceField,
    )

    assert isinstance(
        resolution.get("category").competing[0],
        EvidenceCandidate,
    )
