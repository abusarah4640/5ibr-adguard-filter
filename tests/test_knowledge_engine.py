from scripts.services.knowledge_engine import (
    find_by_category,
    find_by_domain,
    find_by_keyword,
    find_by_technology,
    find_by_vendor,
)


def test_find_by_domain():
    matches = find_by_domain("nrdp.nccp.netflix.com")

    assert matches
    assert matches[0].name == "Netflix"


def test_find_by_keyword():
    matches = find_by_keyword("nrdp")

    assert matches
    assert matches[0].vendor == "Netflix"


def test_find_by_vendor():
    matches = find_by_vendor("Google")

    assert matches
    assert any(entry.name == "YouTube" for entry in matches)


def test_find_by_category():
    matches = find_by_category("Streaming")

    assert matches
    assert any(entry.name == "Netflix" for entry in matches)


def test_find_by_technology():
    matches = find_by_technology("cdn")

    assert matches
    assert any(entry.category == "Streaming" for entry in matches)


def test_empty_queries_return_empty_lists():
    assert find_by_domain("") == []
    assert find_by_keyword("") == []
    assert find_by_vendor("") == []
    assert find_by_category("") == []
    assert find_by_technology("") == []
