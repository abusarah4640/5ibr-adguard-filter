import fivebr

from scripts.version import (
    main as version_main,
)


def test_version_command_registered():
    assert "version" in fivebr.COMMANDS

    assert (
        fivebr.COMMANDS["version"]
        is version_main
    )


def test_version_help_registered():
    assert (
        fivebr.COMMAND_HELP["version"]
        == "Show version"
    )


def test_cli_version_from_source(
    capsys,
):
    result = fivebr.main(
        ["version"]
    )

    captured = capsys.readouterr()

    assert result == 0
    assert captured.out.strip()
