from scripts.intelligence_check import main


def test_intelligence_check_summary_output(capsys):
    exit_code = main([])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "=== Intelligence Check ===" in output
    assert "Knowledge entries" in output
    assert "Vendor groups" in output
    assert "Category groups" in output
    assert "Filter mappings" in output
    assert "Overall status    : HEALTHY" in output
