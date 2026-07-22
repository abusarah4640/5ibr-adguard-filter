from scripts.intelligence_report import build_report, main


def test_build_intelligence_report():
    report = build_report()

    assert "5ibr Intelligence Report" in report
    assert "Knowledge Base" in report
    assert "Rule Engine" in report
    assert "Core Engines" in report
    assert "Database" in report
    assert "Overall" in report


def test_intelligence_report_cli(capsys):
    exit_code = main([])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "5ibr Intelligence Report" in output
    assert "Status             : HEALTHY" in output
