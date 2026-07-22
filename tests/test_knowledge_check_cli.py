from scripts.knowledge_check import main


def test_knowledge_check_cli_success(capsys):
    exit_code = main([])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Knowledge entries:" in output
    assert "Knowledge Base: OK" in output
