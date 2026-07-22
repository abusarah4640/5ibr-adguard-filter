from pathlib import Path


def test_analyzer_service_uses_engines_not_legacy_database_matching():
    source = Path("scripts/services/analyzer_service.py").read_text(encoding="utf-8")

    assert "match_database_evidence" in source
    assert "match_vendor_rules" in source
    assert "match_category_rules" in source
    assert "first_domain_match" in source
    assert "build_decision" in source

    assert "def _known_database_matches" not in source
    assert "from collections import Counter" not in source
