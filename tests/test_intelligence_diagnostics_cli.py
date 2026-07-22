from scripts.intelligence_diagnostics import (
    build_diagnostics_report,
    main,
)


def test_build_diagnostics_report():
    report = build_diagnostics_report()

    assert "5ibr Intelligence Diagnostics" in report
    assert "Knowledge Base [HEALTHY]" in report
    assert "Rule Engine [HEALTHY]" in report
    assert "Decision Engine [HEALTHY]" in report
    assert "Explain Engine [HEALTHY]" in report
    assert "[PASS] entries-loaded" in report
    assert "[PASS] decision-api" in report
    assert "Overall Status: HEALTHY" in report


def test_intelligence_diagnostics_cli(capsys):
    exit_code = main([])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "5ibr Intelligence Diagnostics" in output
    assert "Overall Status: HEALTHY" in output
