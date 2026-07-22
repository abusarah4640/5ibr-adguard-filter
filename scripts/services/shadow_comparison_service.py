"""Compare current Analyzer output with Unified Resolver preview."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scripts.services.canonical_evidence_identity import (
    canonical_evidence_identity,
)
from scripts.services.unified_evidence_resolver import (
    ResolvedEvidenceField,
    UnifiedEvidenceResolution,
)


SUPPORTED_FIELDS = (
    "vendor",
    "category",
    "filter",
)


@dataclass(frozen=True)
class ShadowFieldComparison:
    """Comparison result for one resolved field."""

    field: str
    current_value: str
    preview_value: str
    current_identity: str
    preview_identity: str
    status: str
    preview_score: int = 0
    preview_sources: tuple[str, ...] = field(
        default_factory=tuple
    )
    preview_has_conflict: bool = False
    preview_ambiguous: bool = False
    reason: str = ""

    @property
    def is_match(self) -> bool:
        return self.status == "match"

    @property
    def is_different(self) -> bool:
        return self.status == "different"

    @property
    def is_unresolved(self) -> bool:
        return self.status == "unresolved"

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "current_value": self.current_value,
            "preview_value": self.preview_value,
            "current_identity": self.current_identity,
            "preview_identity": self.preview_identity,
            "status": self.status,
            "is_match": self.is_match,
            "preview_score": self.preview_score,
            "preview_sources": list(
                self.preview_sources
            ),
            "preview_has_conflict": (
                self.preview_has_conflict
            ),
            "preview_ambiguous": (
                self.preview_ambiguous
            ),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ShadowComparison:
    """Shadow comparison for one analyzed domain."""

    domain: str
    fields: dict[str, ShadowFieldComparison]
    current_confidence: int
    current_recommendation: str

    def get(
        self,
        field_name: str,
    ) -> ShadowFieldComparison | None:
        return self.fields.get(
            (field_name or "").strip().lower()
        )

    @property
    def matching_fields(self) -> tuple[str, ...]:
        return tuple(
            field_name
            for field_name in SUPPORTED_FIELDS
            if (
                field_name in self.fields
                and self.fields[field_name].is_match
            )
        )

    @property
    def different_fields(self) -> tuple[str, ...]:
        return tuple(
            field_name
            for field_name in SUPPORTED_FIELDS
            if (
                field_name in self.fields
                and self.fields[
                    field_name
                ].is_different
            )
        )

    @property
    def unresolved_fields(self) -> tuple[str, ...]:
        return tuple(
            field_name
            for field_name in SUPPORTED_FIELDS
            if (
                field_name in self.fields
                and self.fields[
                    field_name
                ].is_unresolved
            )
        )

    @property
    def overall_status(self) -> str:
        if self.different_fields:
            return "different"

        if self.unresolved_fields:
            return "partial"

        return "match"

    @property
    def preview_has_conflicts(self) -> bool:
        return any(
            item.preview_has_conflict
            for item in self.fields.values()
        )

    @property
    def preview_has_ambiguity(self) -> bool:
        return any(
            item.preview_ambiguous
            for item in self.fields.values()
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "overall_status": self.overall_status,
            "matching_fields": list(
                self.matching_fields
            ),
            "different_fields": list(
                self.different_fields
            ),
            "unresolved_fields": list(
                self.unresolved_fields
            ),
            "current_confidence": (
                self.current_confidence
            ),
            "current_recommendation": (
                self.current_recommendation
            ),
            "preview_has_conflicts": (
                self.preview_has_conflicts
            ),
            "preview_has_ambiguity": (
                self.preview_has_ambiguity
            ),
            "fields": {
                field_name: item.to_dict()
                for field_name, item
                in self.fields.items()
            },
        }


def _normalized_current_value(
    value: str,
) -> str:
    normalized = (value or "").strip()

    if normalized.casefold() in {
        "",
        "unknown",
        "none",
        "null",
    }:
        return ""

    return normalized


def compare_shadow_field(
    *,
    field_name: str,
    current_value: str,
    preview: ResolvedEvidenceField | None,
) -> ShadowFieldComparison:
    """Compare one current field with one preview field."""

    normalized_field = (
        field_name or ""
    ).strip().lower()

    current = _normalized_current_value(
        current_value
    )

    current_identity = (
        canonical_evidence_identity(
            normalized_field,
            current,
        )
        if current
        else ""
    )

    if preview is None:
        return ShadowFieldComparison(
            field=normalized_field,
            current_value=current,
            preview_value="",
            current_identity=current_identity,
            preview_identity="",
            status="unresolved",
            reason=(
                "unified resolver did not resolve "
                f"{normalized_field}"
            ),
        )

    preview_identity = preview.identity

    if (
        current_identity
        and preview_identity
        and current_identity == preview_identity
    ):
        status = "match"
        reason = (
            "current and preview values share "
            f"canonical identity: {preview_identity}"
        )
    else:
        status = "different"
        reason = (
            "current and preview values differ: "
            f"{current or 'Unknown'} != "
            f"{preview.value}"
        )

    return ShadowFieldComparison(
        field=normalized_field,
        current_value=current,
        preview_value=preview.value,
        current_identity=current_identity,
        preview_identity=preview_identity,
        status=status,
        preview_score=preview.score,
        preview_sources=preview.sources,
        preview_has_conflict=(
            preview.has_conflict
        ),
        preview_ambiguous=preview.ambiguous,
        reason=reason,
    )


def compare_analyzer_with_resolution(
    *,
    domain: str,
    current_vendor: str,
    current_category: str,
    current_filter: str,
    current_confidence: int,
    current_recommendation: str,
    resolution: UnifiedEvidenceResolution,
) -> ShadowComparison:
    """Compare current Analyzer fields with preview resolution."""

    current_values = {
        "vendor": current_vendor,
        "category": current_category,
        "filter": current_filter,
    }

    comparisons = {
        field_name: compare_shadow_field(
            field_name=field_name,
            current_value=current_values[
                field_name
            ],
            preview=resolution.get(
                field_name
            ),
        )
        for field_name in SUPPORTED_FIELDS
    }

    return ShadowComparison(
        domain=(domain or "").strip().lower(),
        fields=comparisons,
        current_confidence=int(
            current_confidence or 0
        ),
        current_recommendation=(
            current_recommendation
            or "unknown"
        ).strip(),
    )


def compare_analyzer_result(
    result: object,
    resolution: UnifiedEvidenceResolution,
) -> ShadowComparison:
    """Compare an Analyzer result object with preview resolution."""

    return compare_analyzer_with_resolution(
        domain=str(
            getattr(result, "domain", "")
        ),
        current_vendor=str(
            getattr(
                result,
                "suggested_vendor",
                "Unknown",
            )
        ),
        current_category=str(
            getattr(
                result,
                "suggested_category",
                "Unknown",
            )
        ),
        current_filter=str(
            getattr(
                result,
                "suggested_filter",
                "unknown",
            )
        ),
        current_confidence=int(
            getattr(
                result,
                "confidence",
                0,
            )
            or 0
        ),
        current_recommendation=str(
            getattr(
                result,
                "recommendation",
                "unknown",
            )
        ),
        resolution=resolution,
    )
