import json

from scripts.services.analyzer_service import analyze_domain


def write_config(tmp_path, *, categories=None):
    path = tmp_path / "analyzer.json"
    path.write_text(
        json.dumps(
            {
                "vendor_patterns": {
                    "Sony PlayStation": ["playstation.net"],
                },
                "category_keywords": categories or {},
                "filter_map": {
                    "Telemetry": "telemetry",
                    "Gaming": "gaming",
                    "Streaming": "streaming",
                    "Social": "social",
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def test_specific_knowledge_overrides_generic_category_keyword(tmp_path):
    config = write_config(
        tmp_path,
        categories={
            "Telemetry": ["event"],
        },
    )

    result = analyze_domain(
        "event.api.np.km.playstation.net",
        config_path=config,
        rows=[],
    )

    assert result.suggested_vendor == "Sony PlayStation"
    assert result.suggested_category == "Gaming"
    assert result.suggested_filter == "gaming"


def test_database_filter_does_not_override_knowledge_filter(tmp_path):
    config = write_config(tmp_path)

    result = analyze_domain(
        "cdn-0.nflximg.com",
        config_path=config,
        rows=[
            {
                "Domain": "images.nflximg.com",
                "Vendor": "Legacy Vendor",
                "Category": "Social",
                "Filter": "social",
            }
        ],
    )

    assert result.suggested_vendor == "Netflix"
    assert result.suggested_category == "Streaming"
    assert result.suggested_filter == "streaming"


def test_database_filter_still_fills_unknown_filter(tmp_path):
    config = write_config(tmp_path)

    result = analyze_domain(
        "api.example.test",
        config_path=config,
        rows=[
            {
                "Domain": "www.example.test",
                "Vendor": "Example",
                "Category": "Testing",
                "Filter": "privacy",
            }
        ],
    )

    assert result.suggested_filter == "privacy"
