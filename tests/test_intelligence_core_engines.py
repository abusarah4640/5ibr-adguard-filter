from scripts.intelligence_check import main, validate_core_engines


def test_validate_core_engines():
    ok, errors = validate_core_engines()

    assert ok
    assert errors == []


def test_intelligence_check_reports_core_engines(capsys):
    exit_code = main([])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Decision Engine   : OK" in output
    assert "Explain Engine    : OK" in output
