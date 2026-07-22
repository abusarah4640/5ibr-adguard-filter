import json

from scripts.services.analyzer_service import analyze_domain


def test_analyzer_uses_rule_engine_for_vendor_and_category(tmp_path):
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

    assert result.suggested_vendor == "ExampleVendor"
    assert result.suggested_category == "Streaming"
    assert result.suggested_filter == "streaming"
    assert result.confidence == 65
    assert result.recommendation == "review"
    assert "matched known vendor namespace: example.com" in result.reasons
    assert "matched category keyword: video" in result.reasons
