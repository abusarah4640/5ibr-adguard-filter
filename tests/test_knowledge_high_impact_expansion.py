from scripts.services.analyzer_service import analyze_domain
from scripts.services.knowledge_engine import first_domain_match


def test_lg_smart_tv_knowledge():
    entry = first_domain_match("sa.rdx2.lgtvsdp.com")

    assert entry is not None
    assert entry.name == "LG Smart TV"
    assert entry.vendor == "LG"
    assert entry.category == "Smart TV"
    assert entry.filter_name == "smart-tv"

    result = analyze_domain("sa.rdx2.lgtvsdp.com", rows=[])

    assert result.suggested_vendor == "LG"
    assert result.suggested_category == "Smart TV"
    assert result.suggested_filter == "smart-tv"


def test_google_ads_knowledge():
    entry = first_domain_match("www.googleadservices.com")

    assert entry is not None
    assert entry.name == "Google Ads"
    assert entry.vendor == "Google"
    assert entry.category == "Ads"
    assert entry.filter_name == "ads"

    result = analyze_domain("www.googleadservices.com", rows=[])

    assert result.suggested_vendor == "Google"
    assert result.suggested_category == "Ads"
    assert result.suggested_filter == "ads"


def test_epic_games_knowledge():
    entry = first_domain_match("datarouter.ol.epicgames.com")

    assert entry is not None
    assert entry.name == "Epic Games"
    assert entry.vendor == "Epic Games"
    assert entry.category == "Gaming"
    assert entry.filter_name == "gaming"

    result = analyze_domain("datarouter.ol.epicgames.com", rows=[])

    assert result.suggested_vendor == "Epic Games"
    assert result.suggested_category == "Gaming"
    assert result.suggested_filter == "gaming"
