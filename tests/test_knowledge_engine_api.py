from scripts.services.knowledge_engine import (
    explain_domain_match,
    first_domain_match,
)


def test_first_domain_match():
    entry = first_domain_match("nrdp.nccp.netflix.com")

    assert entry is not None
    assert entry.vendor == "Netflix"


def test_explain_domain_match():
    reasons = explain_domain_match("event.api.np.km.playstation.net")

    assert reasons
    assert any("PlayStation Network" in reason for reason in reasons)
