from scripts.services.database_evidence_engine import (
    DatabaseEvidence,
    match_database_evidence,
)


def test_match_database_evidence_exact_domain():
    evidence = match_database_evidence(
        "api.netflix.com",
        [
            {
                "Domain": "api.netflix.com",
                "Vendor": "Netflix",
                "Category": "Streaming",
                "Filter": "streaming",
            }
        ],
    )

    assert isinstance(evidence, DatabaseEvidence)
    assert evidence.vendor == "Netflix"
    assert evidence.category == "Streaming"
    assert evidence.filter_name == "streaming"
    assert evidence.score == 35
    assert "matched existing database domain: api.netflix.com" in evidence.reasons


def test_match_database_evidence_root_domain():
    evidence = match_database_evidence(
        "nrdp.netflix.com",
        [
            {
                "Domain": "api.netflix.com",
                "Vendor": "Netflix",
                "Category": "Streaming",
                "Filter": "streaming",
            }
        ],
    )

    assert evidence.vendor == "Netflix"
    assert evidence.category == "Streaming"
    assert evidence.filter_name == "streaming"
    assert evidence.score == 20
    assert "matched existing database root: netflix.com" in evidence.reasons


def test_match_database_evidence_no_match():
    evidence = match_database_evidence(
        "unknown.example",
        [
            {
                "Domain": "api.netflix.com",
                "Vendor": "Netflix",
                "Category": "Streaming",
                "Filter": "streaming",
            }
        ],
    )

    assert evidence.vendor == ""
    assert evidence.category == ""
    assert evidence.filter_name == ""
    assert evidence.score == 0
    assert evidence.reasons == []
