"""Contract tests for the production Web deployment artifacts."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_systemd_template_is_loopback_only_and_uses_environment_file():
    text = (
        PROJECT_ROOT
        / "deploy"
        / "fivebr-web.service"
    ).read_text(encoding="utf-8")

    assert "EnvironmentFile=/etc/fivebr-web.env" in text
    assert "--bind 127.0.0.1:8089" in text
    assert "--bind 0.0.0.0:8089" not in text
    assert "Environment=FIVEBR_SECRET_KEY" not in text
    assert "web.app:app" in text


def test_environment_example_requires_production_security():
    text = (
        PROJECT_ROOT
        / "deploy"
        / "fivebr-web.env.example"
    ).read_text(encoding="utf-8")

    assert "FIVEBR_ENV=production" in text
    assert "FIVEBR_COOKIE_SECURE=true" in text
    assert "FIVEBR_TRUSTED_HOSTS=filters.example.com" in text
    assert (
        "FIVEBR_SECRET_KEY=<generate-a-random-secret>"
        in text
    )


def test_runbook_documents_health_firewall_and_safe_rollback():
    runbook = (
        PROJECT_ROOT
        / "docs"
        / "production-web-deployment.md"
    ).read_text(encoding="utf-8")
    web_ui = (
        PROJECT_ROOT
        / "docs"
        / "web-ui.md"
    ).read_text(encoding="utf-8")

    assert "127.0.0.1:8089" in runbook
    assert "seq 1 30" in runbook
    assert "Secure" in runbook
    assert "untrusted Host" in runbook
    assert "ufw --force delete allow 8089/tcp" in runbook
    assert "Never restore a unit" in runbook
    assert "Recovery drill record" in runbook
    assert "docs/production-web-deployment.md" in web_ui
