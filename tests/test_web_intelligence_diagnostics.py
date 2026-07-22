from pathlib import Path


def test_intelligence_route_builds_diagnostics():
    source = Path("web/app.py").read_text(encoding="utf-8")

    assert "build_intelligence_diagnostics()" in source
    assert "diagnostics=diagnostics" in source


def test_intelligence_template_displays_diagnostics():
    source = Path("web/templates/intelligence.html").read_text(
        encoding="utf-8"
    )

    assert "diagnostics.status" in source
    assert "diagnostics.components" in source
    assert "component.checks" in source
    assert "check.name" in source
    assert "check.detail" in source
    assert "check.ok" in source


def test_intelligence_diagnostics_translations_exist():
    source = Path("web/i18n.py").read_text(encoding="utf-8")

    assert '"intelligence_diagnostics"' in source
    assert '"diagnostic_checks"' in source
    assert '"check_passed"' in source
    assert '"check_failed"' in source
