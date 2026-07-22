from scripts.intelligence_check import main


def test_intelligence_check_cli(capsys):
    exit_code = main([])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Knowledge status" in output
    assert "Rule status" in output
    assert "Overall status" in output
    assert "HEALTHY" in output
