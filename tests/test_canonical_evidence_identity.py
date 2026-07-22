from scripts.services.canonical_evidence_identity import (
    canonical_evidence_identity,
    canonical_vendor_identity,
    normalize_identity_text,
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


def make_vendor(
    source: str,
    value: str,
    score: int,
):
    return make_unified_evidence(
        source=source,
        field="vendor",
        value=value,
        quality=EvidenceQuality.STRONG,
        score=score,
        reason=f"{source} vendor evidence",
    )


def test_identity_text_normalization():
    assert (
        normalize_identity_text(
            " Sony__PlayStation "
        )
        == "sony playstation"
    )

    assert (
        normalize_identity_text(
            "Facebook, Inc."
        )
        == "facebook inc"
    )


def test_sony_vendor_aliases_share_one_identity():
    expected = "sony-playstation"

    assert canonical_vendor_identity("Sony") == expected
    assert (
        canonical_vendor_identity(
            "Sony PlayStation"
        )
        == expected
    )
    assert (
        canonical_vendor_identity("PlayStation")
        == expected
    )
    assert canonical_vendor_identity("PSN") == expected


def test_meta_vendor_aliases_share_one_identity():
    assert canonical_vendor_identity("Meta") == "meta"
    assert (
        canonical_vendor_identity("Facebook")
        == "meta"
    )
    assert (
        canonical_vendor_identity(
            "Facebook Inc."
        )
        == "meta"
    )


def test_google_and_google_ads_remain_distinct():
    assert (
        canonical_evidence_identity(
            "vendor",
            "Google",
        )
        == "google"
    )

    assert (
        canonical_evidence_identity(
            "vendor",
            "Google Ads",
        )
        == "google ads"
    )

    assert (
        canonical_evidence_identity(
            "vendor",
            "Google",
        )
        != canonical_evidence_identity(
            "vendor",
            "Google Ads",
        )
    )


def test_bundle_uses_canonical_vendor_identity():
    bundle = UnifiedEvidenceBundle(
        domain="event.api.playstation.net",
        evidence=[
            make_vendor(
                "rule",
                "Sony",
                35,
            ),
            make_vendor(
                "knowledge",
                "Sony PlayStation",
                50,
            ),
            make_vendor(
                "database",
                "SONY-PLAYSTATION",
                20,
            ),
        ],
    )

    assert bundle.value_conflicts() == {}
    assert bundle.conflicting_fields() == []
    assert not bundle.has_conflicts()
