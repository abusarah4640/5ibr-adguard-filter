import json

from scripts.services.analyzer_service import analyze_domain


def test_analyzer_uses_decision_engine_for_confidence_and_recommendation(tmp_path):
    config_file = tmp_path / "analyzer.json"
    config_file.write_text(
        json.dumps(
            {
                "vendor_patterns": {
                    "ExampleVendor": ["example.com"]
                },
                "category_keywords": {
                    "Streaming": ["video"]
                },
                "filter_map": {
                    "Streaming": "streaming"
                },
            }
        ),
        encoding="utf-8",
    )

    result = analyze_domain(
        "video-api.example.com",
        config_path=config_file,
        rows=[],
    )

    assert result.confidence == 65
    assert result.recommendation == "review"
    assert result.suggested_vendor == "ExampleVendor"
    assert result.suggested_category == "Streaming"
    assert result.suggested_filter == "streaming"
    assert "confidence score from analyzer evidence" not in result.reasons


def test_analyzer_unknown_result_still_has_default_reason(tmp_path):
    config_file = tmp_path / "analyzer.json"
    config_file.write_text(
        json.dumps(
            {
                "vendor_patterns": {},
                "category_keywords": {},
                "filter_map": {},
            }
        ),
        encoding="utf-8",
    )

    result = analyze_domain(
        "unknown-random-domain.example",
        config_path=config_file,
        rows=[],
    )

    assert result.confidence == 0
    assert result.recommendation == "unknown"
    assert result.reasons == ["no local analyzer rules matched"]
