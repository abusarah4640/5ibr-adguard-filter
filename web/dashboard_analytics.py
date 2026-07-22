"""Read-only presentation helpers for dashboard analytics."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, Mapping
from datetime import datetime, timedelta, timezone as datetime_timezone
from zoneinfo import ZoneInfo


LOW_CONFIDENCE_THRESHOLD = 50
UNKNOWN_VALUE = "Unknown"


def _text(value: object) -> str:
    return str(value or "").strip()


def _score(value: object) -> int:
    try:
        return int(_text(value))
    except ValueError:
        return 0


def _distribution(rows: list[Mapping[str, object]], field: str) -> list[dict[str, object]]:
    total = len(rows)
    counts = Counter(_text(row.get(field)) or UNKNOWN_VALUE for row in rows)
    return [
        {
            "name": name,
            "count": count,
            "percent": round(count / total * 100, 1) if total else 0.0,
        }
        for name, count in counts.most_common(5)
    ]


def domain_analytics(rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Summarize existing domain rows without changing their stored values."""
    items = list(rows)
    confidence = [_score(row.get("Confidence")) for row in items]
    approved = sum(1 for row in items if (_text(row.get("Status")) or "Approved") == "Approved")
    high = sum(score >= 80 for score in confidence)
    medium = sum(50 <= score < 80 for score in confidence)
    low = sum(score < 50 for score in confidence)
    total = len(items)
    return {
        "total": len(items),
        "approved": approved,
        "pending": len(items) - approved,
        "unique_vendors": len({_text(row.get("Vendor")) for row in items if _text(row.get("Vendor"))}),
        "unique_categories": len({_text(row.get("Category")) for row in items if _text(row.get("Category"))}),
        "unique_filters": len({_text(row.get("Filter")) for row in items if _text(row.get("Filter"))}),
        "average_confidence": round(sum(confidence) / len(items), 1) if items else 0.0,
        "low_confidence": low,
        "low_confidence_threshold": LOW_CONFIDENCE_THRESHOLD,
        "top_vendors": _distribution(items, "Vendor"),
        "top_categories": _distribution(items, "Category"),
        "top_filters": _distribution(items, "Filter"),
        "confidence_distribution": (
            {"key": "high", "count": high, "percent": round(high / total * 100, 1) if total else 0.0},
            {"key": "medium", "count": medium, "percent": round(medium / total * 100, 1) if total else 0.0},
            {"key": "low", "count": low, "percent": round(low / total * 100, 1) if total else 0.0},
        ),
        "status_distribution": (
            {"key": "approved", "count": approved, "percent": round(approved / total * 100, 1) if total else 0.0},
            {"key": "pending", "count": total - approved, "percent": round((total - approved) / total * 100, 1) if total else 0.0},
        ),
    }


_TEST_MARKERS = ("example.test", "buildfail.test", "approve.test")


def is_test_event(event: Mapping[str, object]) -> bool:
    combined = " ".join(_text(value).lower() for value in event.values())
    return "/tmp/pytest-" in combined or "\\tmp\\pytest-" in combined or any(
        marker in combined for marker in _TEST_MARKERS
    )


def display_events(
    events: Iterable[Mapping[str, object]], *, testing: bool = False
) -> list[Mapping[str, object]]:
    """Filter test artifacts from production presentation only."""
    return [event for event in events if testing or not is_test_event(event)]


def _event_metadata(details: str) -> tuple[str, str, str]:
    duration = re.search(r"(?:duration|elapsed)\s*[=:]\s*([\d.]+\s*(?:ms|s|sec|seconds?)?)", details, re.I)
    issues = re.search(r"(?:issues?|problems?|errors?)\s*[=:]\s*(\d+)", details, re.I)
    exit_code = re.search(r"(?:exit(?:\s+code)?|code)\s*[=:]\s*(-?\d+)", details, re.I)
    return (
        duration.group(1) if duration else "",
        issues.group(1) if issues else "",
        exit_code.group(1) if exit_code else "",
    )


def operational_activity(
    events: Iterable[Mapping[str, object]], *, testing: bool = False
) -> list[dict[str, object]]:
    """Return the latest real audit event for each dashboard operation."""
    definitions = (
        ("build", ("action.build", "review_queue.build"), "audit_log"),
        ("validate", ("action.validate",), "audit_log"),
        ("doctor", ("action.doctor",), "audit_log"),
        ("intelligence", ("action.intelligence-check",), "intelligence_report_page"),
    )
    rows = list(events)
    cards: list[dict[str, object]] = []
    for key, actions, endpoint in definitions:
        selected = next((
            event for event in rows
            if _text(event.get("Action")) in actions and (testing or not is_test_event(event))
        ), None)
        if selected is None:
            cards.append({"key": key, "status": "none", "endpoint": endpoint})
            continue
        result = _text(selected.get("Result")).lower()
        status = "success" if result in {"ok", "success", "passed"} else (
            "failure" if result in {"error", "failed", "failure"} else "warning"
        )
        duration, issues, exit_code = _event_metadata(_text(selected.get("Details")))
        cards.append({
            "key": key,
            "status": status,
            "timestamp": _text(selected.get("Timestamp")),
            "duration": duration,
            "issues": issues,
            "exit_code": exit_code,
            "endpoint": endpoint,
        })
    return cards


def readiness_display_state(readiness: object | None) -> str:
    """Classify readiness for display without changing readiness decisions."""
    if readiness is None:
        return "insufficient_data"
    if bool(getattr(readiness, "ready", False)):
        return "ready"
    failed_keys = {
        check.key for check in getattr(readiness, "diagnostics", ())
        if not check.passed
    }
    hard_failures = {"unclassified-approvals", "classified-block-rate", "enforce-rows"}
    return "failed" if failed_keys & hard_failures else "insufficient_data"


def readiness_next_action(readiness: object | None, display_state: str) -> dict[str, str]:
    """Choose one read-only next-step link from the displayed readiness state."""
    if display_state == "ready":
        return {"key": "monitor_operational_activity", "endpoint": "audit_log"}
    if readiness is not None:
        progress = getattr(readiness, "progress", None)
        if progress is not None and getattr(progress, "classified_approvals_remaining", 0) > 0:
            return {"key": "collect_approval_history", "endpoint": "review_queue"}
    if display_state == "failed":
        return {"key": "review_failed_checks", "endpoint": "audit_log"}
    return {"key": "run_system_check", "endpoint": "dashboard"}


def audit_operation_key(action: object) -> str:
    value = _text(action).lower()
    for key in ("intelligence-check", "build", "validate", "doctor"):
        if value == key or value == f"action.{key}" or value.endswith(f".{key}"):
            return key.replace("-", "_")
    return ""


def format_display_datetime(value: object, timezone: str = "UTC", date_format: str = "yyyy-mm-dd") -> str:
    """Format an audit timestamp for display while preserving its stored value."""
    text = _text(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        try:
            destination = ZoneInfo(timezone or "UTC")
        except KeyError:
            fallback_offsets = {"UTC": 0, "Asia/Riyadh": 3}
            if timezone not in fallback_offsets:
                return text
            destination = datetime_timezone(timedelta(hours=fallback_offsets[timezone]))
        parsed = parsed.astimezone(destination)
    except (ValueError, TypeError):
        return text
    formats = {"yyyy-mm-dd": "%Y-%m-%d %H:%M", "dd/mm/yyyy": "%d/%m/%Y %H:%M", "mm/dd/yyyy": "%m/%d/%Y %H:%M"}
    return parsed.strftime(formats.get(date_format, formats["yyyy-mm-dd"]))
