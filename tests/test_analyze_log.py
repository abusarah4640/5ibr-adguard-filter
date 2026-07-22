from __future__ import annotations

import csv
import json

from scripts.analyze_log import main as analyze_log_main
from scripts.services.querylog_service import analyze_query_log, extract_query_domains


ROWS = [
    {
        "Domain": "doubleclick.net",
        "Vendor": "Google",
        "Category": "Ads",
        "Filter": "ads",
        "Confidence": "100",
        "Status": "Approved",
    }
]


def test_extract_query_domains_from_adguard_records(tmp_path):
    querylog = tmp_path / "querylog.json"
    querylog.write_text(
        "\n".join(
            [
                json.dumps({"QH": "mobile.events.data.microsoft.com", "QT": "A"}),
                json.dumps({"question": {"host": "doubleclick.net"}}),
                json.dumps({"QH": "mobile.events.data.microsoft.com", "QT": "AAAA"}),
            ]
        ),
        encoding="utf-8",
    )

    counts = extract_query_domains(querylog)

    assert counts["mobile.events.data.microsoft.com"] == 2
    assert counts["doubleclick.net"] == 1


def test_analyze_query_log_skips_known_and_writes_reports(tmp_path):
    querylog = tmp_path / "querylog.json"
    reports = tmp_path / "reports"
    querylog.write_text(
        json.dumps(
            [
                {"QH": "doubleclick.net"},
                {"QH": "mobile.events.data.microsoft.com"},
                {"QH": "mobile.events.data.microsoft.com"},
                {"QH": "graph.facebook.com"},
            ]
        ),
        encoding="utf-8",
    )

    result = analyze_query_log(
        querylog,
        min_seen=1,
        limit=10,
        rows=ROWS,
        reports_dir=reports,
    )

    domains = [suggestion.domain for suggestion in result.suggestions]
    assert "doubleclick.net" not in domains
    assert domains[0] == "mobile.events.data.microsoft.com"
    assert result.suggestions[0].seen == 2
    assert result.suggestions[0].analysis.suggested_vendor == "Microsoft"
    assert (reports / "suggestions.csv").exists()
    assert (reports / "suggestions.md").exists()

    with (reports / "suggestions.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["Domain"] == "mobile.events.data.microsoft.com"


def test_analyze_query_log_min_seen_and_limit(tmp_path):
    querylog = tmp_path / "querylog.json"
    querylog.write_text(
        "\n".join(
            [
                json.dumps({"QH": "mobile.events.data.microsoft.com"}),
                json.dumps({"QH": "mobile.events.data.microsoft.com"}),
                json.dumps({"QH": "graph.facebook.com"}),
            ]
        ),
        encoding="utf-8",
    )

    result = analyze_query_log(
        querylog,
        min_seen=2,
        limit=1,
        rows=[],
        write_reports=False,
    )

    assert len(result.suggestions) == 1
    assert result.suggestions[0].domain == "mobile.events.data.microsoft.com"


def test_analyze_log_command_outputs_summary(tmp_path, capsys):
    querylog = tmp_path / "querylog.json"
    querylog.write_text(json.dumps([{"QH": "unknown.example.test"}]), encoding="utf-8")

    exit_code = analyze_log_main([str(querylog), "--limit", "1"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "5ibr Query Log Analysis" in output
    assert "unknown.example.test" in output
    assert "Reports" in output
