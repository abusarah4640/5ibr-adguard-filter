from scripts.services.semantic_filter_mapping import (
    compare_filter_mappings,
    semantic_filter_for_category,
)


def test_semantic_category_filter_mapping():
    assert (
        semantic_filter_for_category("Streaming")
        == "streaming"
    )

    assert (
        semantic_filter_for_category("Gaming")
        == "gaming"
    )

    assert (
        semantic_filter_for_category("Smart TV")
        == "smart-tv"
    )

    assert (
        semantic_filter_for_category("Mobile")
        == "mobile"
    )


def test_semantic_mapping_is_case_insensitive():
    assert (
        semantic_filter_for_category("streaming")
        == "streaming"
    )

    assert (
        semantic_filter_for_category("SMART-TV")
        == "smart-tv"
    )


def test_detects_legacy_mapping_differences():
    configured = {
        "Streaming": "social",
        "Connectivity": "privacy",
        "Ads": "ads",
    }

    differences = compare_filter_mappings(
        configured
    )

    by_category = {
        item["category"]: item
        for item in differences
    }

    assert by_category["Streaming"] == {
        "category": "Streaming",
        "configured_filter": "social",
        "semantic_filter": "streaming",
    }

    assert by_category["Connectivity"] == {
        "category": "Connectivity",
        "configured_filter": "privacy",
        "semantic_filter": "connectivity",
    }

    assert "Ads" not in by_category
