from __future__ import annotations

import csv

from scripts import database
from scripts.services.integrity_service import validate_row
from scripts.services.review_service import pending_domains, set_review_status, submit_domain


def _write_db(path):
    path.write_text(
        "Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes\n",
        encoding="utf-8",
    )


def test_integrity_rejects_invalid_confidence():
    result = validate_row(
        {
            "Domain": "example.com",
            "Vendor": "Example",
            "Category": "Telemetry",
            "Filter": "telemetry",
            "Confidence": "101",
            "Status": "Approved",
        }
    )
    assert not result.ok
    assert any("Confidence" in error for error in result.errors)


def test_review_workflow_submit_and_approve(monkeypatch, tmp_path):
    csv_file = tmp_path / "domains.csv"
    _write_db(csv_file)
    monkeypatch.setattr(database, "DATABASE", csv_file)

    ok, errors = submit_domain(
        domain="pending.example",
        vendor="Example",
        category="Telemetry",
        filter_name="telemetry",
        confidence=80,
        source="Manual",
        evidence="https://example.com/evidence",
    )

    assert ok, errors
    assert len(pending_domains()) == 1

    ok, errors = set_review_status("pending.example", "Approved", reviewer="ibrahim")
    assert ok, errors

    rows = list(csv.DictReader(csv_file.open(encoding="utf-8")))
    assert rows[0]["Status"] == "Approved"
    assert rows[0]["Reviewer"] == "ibrahim"
