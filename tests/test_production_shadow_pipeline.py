import json

from scripts.services.production_shadow_pipeline import (
    category_filter_matches,
    load_suggestion_rows,
    run_production_shadow_evaluation,
    write_production_shadow_reports,
)
from scripts.services.rule_engine import RuleMatch


def test_category_filter_matches():
    category = RuleMatch(
        rule_type="category",
        value="Gaming",
        score=30,
        reason="matched category keyword: game",
        metadata={
            "keyword": "game",
            "evidence_quality": "MODERATE",
            "evidence_reason": "keyword match: game",
        },
    )

    matches = category_filter_matches(
        [category],
        {
            "Gaming": "gaming",
        },
    )

    assert len(matches) == 1

    match = matches[0]

    assert match.rule_type == "filter"
    assert match.value == "gaming"
    assert match.score == 30
    assert (
        match.metadata["derived_category"]
        == "Gaming"
    )


def test_load_suggestion_rows(tmp_path):
    path = tmp_path / "suggestions.json"

    path.write_text(
        json.dumps(
            {
                "suggestions": [
                    {
                        "domain": "example.com",
                        "vendor": "Example",
                    },
                    {
                        "domain": "",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    rows = load_suggestion_rows(path)

    assert len(rows) == 1
    assert rows[0]["domain"] == "example.com"


def test_run_production_shadow_evaluation(tmp_path):
    suggestions = tmp_path / "suggestions.json"
    config = tmp_path / "analyzer.json"

    suggestions.write_text(
        json.dumps(
            {
                "suggestions": [
                    {
                        "domain": "event.api.playstation.net",
                        "vendor": "Sony PlayStation",
                        "category": "Gaming",
                        "filter": "gaming",
                        "confidence": 89,
                        "recommendation": "review",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    config.write_text(
        json.dumps(
            {
                "vendor_patterns": {
                    "Sony": [
                        "playstation.net"
                    ]
                },
                "category_keywords": {
                    "Telemetry": [
                        "event"
                    ]
                },
                "filter_map": {
                    "Telemetry": "telemetry",
                    "Gaming": "gaming",
                },
            }
        ),
        encoding="utf-8",
    )

    rows = [
        {
            "Domain": "api.playstation.net",
            "Vendor": "Sony PlayStation",
            "Category": "Gaming",
            "Filter": "gaming",
        }
    ]

    result = run_production_shadow_evaluation(
        suggestions,
        config_path=config,
        database_rows=rows,
    )

    assert result.summary.domains_compared == 1
    assert result.summary.full_matches == 1
    assert result.summary.different_decisions == 0

    comparison = result.comparisons[0]

    assert comparison.overall_status == "match"
    assert comparison.preview_has_conflicts
    assert comparison.get("vendor").is_match
    assert comparison.get("category").is_match
    assert comparison.get("filter").is_match


def test_write_production_shadow_reports(tmp_path):
    suggestions = tmp_path / "suggestions.json"
    config = tmp_path / "analyzer.json"

    suggestions.write_text(
        json.dumps(
            {
                "suggestions": [
                    {
                        "domain": "google.com",
                        "vendor": "Google",
                        "category": "Unknown",
                        "filter": "unknown",
                        "confidence": 35,
                        "recommendation": "unknown",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    config.write_text(
        json.dumps(
            {
                "vendor_patterns": {
                    "Google": ["google.com"]
                },
                "category_keywords": {},
                "filter_map": {},
            }
        ),
        encoding="utf-8",
    )

    result = run_production_shadow_evaluation(
        suggestions,
        config_path=config,
        database_rows=[],
    )

    text_path = tmp_path / "report.txt"
    json_path = tmp_path / "report.json"
    comparisons_path = (
        tmp_path / "comparisons.json"
    )

    write_production_shadow_reports(
        result,
        text_path=text_path,
        json_path=json_path,
        comparisons_path=comparisons_path,
    )

    assert text_path.exists()
    assert json_path.exists()
    assert comparisons_path.exists()

    assert (
        "5ibr Shadow Evaluation Report"
        in text_path.read_text(encoding="utf-8")
    )

    payload = json.loads(
        json_path.read_text(encoding="utf-8")
    )

    assert payload["summary"][
        "domains_compared"
    ] == 1
