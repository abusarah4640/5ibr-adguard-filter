import sys

import fivebr


def test_command_registry_contains_supported_commands():

    assert set(fivebr.COMMANDS) == {
        "add",
        "build",
        "remove",
        "report",
        "search",
        "stats",
        "validate",
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
