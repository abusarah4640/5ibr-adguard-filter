from scripts.services.knowledge_service import (
    KnowledgeEntry,
    explain_knowledge_match,
    load_knowledge_entries,
    match_knowledge,
    normalize_text,
)


def test_load_default_knowledge_entries():
    entries = load_knowledge_entries()

    assert entries
    assert all(isinstance(entry, KnowledgeEntry) for entry in entries)


def test_normalize_text():
    assert normalize_text("  Netflix.COM  ") == "netflix.com"
    assert normalize_text("") == ""


def test_match_knowledge_by_keyword():
    matches = match_knowledge("nrdp.nccp.netflix.com")

    assert matches
    assert matches[0].vendor == "Netflix"
    assert matches[0].category == "Streaming"
    assert matches[0].filter_name == "streaming"


def test_match_knowledge_no_match():
    assert match_knowledge("unknown-random-domain.example") == []


def test_explain_knowledge_match():
    reasons = explain_knowledge_match("event.api.np.km.playstation.net")

    assert reasons
    assert any("PlayStation Network" in reason for reason in reasons)
    assert any("keyword" in reason for reason in reasons)

from scripts.services.analyzer_service import analyze_domain


def test_analyzer_uses_knowledge_base():
    result = analyze_domain("nrdp.nccp.netflix.com", rows=[])

    assert result.suggested_vendor == "Netflix"
    assert result.suggested_category == "Streaming"
    assert result.suggested_filter == "streaming"
    assert any("knowledge matched" in reason.lower() for reason in result.reasons)


def test_load_knowledge_entries_from_json_file(tmp_path):
    knowledge_file = tmp_path / "knowledge.json"
    knowledge_file.write_text(
        """
[
  {
    "name": "Test Service",
    "kind": "service",
    "keywords": ["test-service"],
    "vendor": "TestVendor",
    "category": "Testing",
    "filter_name": "testing",
    "technologies": ["unit-test"]
  }
]
""",
        encoding="utf-8",
    )

    entries = load_knowledge_entries(knowledge_file)

    assert len(entries) == 1
    assert entries[0].name == "Test Service"
    assert entries[0].vendor == "TestVendor"
    assert entries[0].category == "Testing"
    assert entries[0].filter_name == "testing"


from scripts.services.knowledge_service import (
    knowledge_integrity_report,
    validate_knowledge_entries,
)


def test_validate_knowledge_entries_success():
    entries = load_knowledge_entries()

    ok, errors = validate_knowledge_entries(entries)

    assert ok
    assert errors == []


def test_validate_knowledge_entries_errors():
    bad_entry = KnowledgeEntry(
        name="",
        kind="",
        keywords=(),
        vendor="",
        category="",
        filter_name="",
    )

    ok, errors = validate_knowledge_entries([bad_entry])

    assert not ok
    assert errors
    assert any("name is required" in error for error in errors)
    assert any("at least one keyword is required" in error for error in errors)


def test_knowledge_integrity_report():
    ok, errors = knowledge_integrity_report()

    assert ok
    assert errors == []
