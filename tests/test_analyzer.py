from scripts.services.analyzer_service import analyze_domain, root_domain


def test_microsoft_telemetry_domain():
    result = analyze_domain("mobile.events.data.microsoft.com")
    assert result.root_domain == "microsoft.com"
    assert result.suggested_vendor == "Microsoft"
    assert result.suggested_category == "Telemetry"
    assert result.suggested_filter == "telemetry"
    assert result.confidence >= 90
    assert result.recommendation == "approved-candidate"


def test_google_ads_domain():
    result = analyze_domain("doubleclick.net")
    assert result.suggested_vendor == "Google"
    assert result.suggested_category == "Ads"
    assert result.suggested_filter == "ads"
    assert result.confidence >= 90


def test_meta_social_domain():
    result = analyze_domain("connect.facebook.net")
    assert result.suggested_vendor == "Meta"
    assert result.suggested_category == "Social"
    assert result.suggested_filter == "social"
    assert result.confidence >= 90


def test_unknown_domain():
    result = analyze_domain("unknown-random-example.invalid")
    assert result.suggested_vendor == "Unknown"
    assert result.suggested_category == "Unknown"
    assert result.suggested_filter == "unknown"
    assert result.recommendation == "unknown"


def test_existing_database_similarity_pattern_match():
    rows = [
        {
            "Domain": "metrics.examplevendor.com",
            "Vendor": "Example Vendor",
            "Category": "Telemetry",
            "Filter": "telemetry",
        }
    ]
    result = analyze_domain("events.examplevendor.com", rows=rows)
    assert root_domain(result.domain) == "examplevendor.com"
    assert result.suggested_vendor == "Example Vendor"
    assert result.suggested_category == "Telemetry"
    assert result.suggested_filter == "telemetry"
    assert result.recommendation == "review"
