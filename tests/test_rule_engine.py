from scripts.services.rule_engine import (
    RuleMatch,
    first_match,
    match_category_rules,
    match_vendor_rules,
    matches_pattern,
    normalize_rule_text,
    total_score,
)


def test_normalize_rule_text():
    assert normalize_rule_text("  Netflix.COM  ") == "netflix.com"
    assert normalize_rule_text("") == ""


def test_matches_pattern_exact_suffix_and_contains():
    assert matches_pattern("netflix.com", "netflix.com")
    assert matches_pattern("api.netflix.com", "netflix.com")
    assert matches_pattern("nrdp.nccp.netflix.com", "nccp")


def test_matches_pattern_empty_values():
    assert not matches_pattern("", "netflix")
    assert not matches_pattern("netflix.com", "")


def test_match_vendor_rules():
    matches = match_vendor_rules(
        "nrdp.nccp.netflix.com",
        {"Netflix": ["netflix.com", "nccp"]},
    )

    assert matches
    assert matches[0].rule_type == "vendor"
    assert matches[0].value == "Netflix"
    assert matches[0].score == 35


def test_match_category_rules():
    matches = match_category_rules(
        "video-api.example.com",
        {"Streaming": ["video"]},
    )

    assert matches
    assert matches[0].rule_type == "category"
    assert matches[0].value == "Streaming"
    assert matches[0].score == 30


def test_first_match():
    matches = [
        RuleMatch(rule_type="vendor", value="Netflix", score=35, reason="vendor"),
        RuleMatch(rule_type="category", value="Streaming", score=30, reason="category"),
    ]

    assert first_match(matches, "category").value == "Streaming"
    assert first_match(matches, "missing") is None


def test_total_score():
    matches = [
        RuleMatch(rule_type="vendor", value="Netflix", score=35, reason="vendor"),
        RuleMatch(rule_type="category", value="Streaming", score=30, reason="category"),
    ]

    assert total_score(matches) == 65
