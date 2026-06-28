from pathlib import Path


def test_cli_exists():

    assert Path("fivebr.py").exists()