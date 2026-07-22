import sys

import fivebr


def test_command_registry_contains_supported_commands():

    assert set(fivebr.COMMANDS) == {
        "add",
        "analyze",
        "analyze-log",
        "confidence-impact",
        "conflict-impact",
        "build",
        "remove",
        "review",
        "rule-check",
        "list",
        "doctor",
        "normalize",
        "export",
        "import",
        "knowledge-check",
        "intelligence-check",
        "intelligence-diagnostics",
        "intelligence-report",
        "report",
        "project-status",
        "search",
        "stats",
        "update",
        "validate",
                                       "version",
                                       "init",
    }


def test_router_dispatches_command_argv_without_mutating_sys_argv(monkeypatch):

    received = []
    original_argv = sys.argv[:]

    def fake_search(argv):
        received.append(argv)
        return 0

    monkeypatch.setitem(fivebr.COMMANDS, "search", fake_search)

    assert fivebr.main(["search", "example.com"]) == 0
    assert received == [["example.com"]]
    assert sys.argv == original_argv


def test_update_command_appears_in_help():

    help_text = fivebr.build_parser().format_help()

    assert "update" in help_text
    assert "doctor" in help_text
    assert "list" in help_text
    assert "review" in help_text
