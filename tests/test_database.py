from io import StringIO

from scripts import database
import fivebr


def test_add_domain_preserves_extra_columns(monkeypatch, tmp_path):

    csv_file = tmp_path / "domains.csv"
    csv_file.write_text(
        "Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes\n"
        "example.com,Example,Telemetry,telemetry,90,Approved,Manual,Seed\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert database.add_domain(
        domain="new.example.com",
        vendor="Example",
        category="Telemetry",
        filter_name="telemetry",
        confidence=80,
    )

    lines = csv_file.read_text(encoding="utf-8").splitlines()

    assert lines[0] == "Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes"
    assert "example.com,Example,Telemetry,telemetry,90,Approved,Manual,Seed" in lines
    assert "new.example.com,Example,Telemetry,telemetry,80,,," in lines


def test_remove_domain_preserves_extra_columns(monkeypatch, tmp_path):

    csv_file = tmp_path / "domains.csv"
    csv_file.write_text(
        "Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes\n"
        "keep.example.com,Example,Telemetry,telemetry,90,Approved,Manual,Keep\n"
        "remove.example.com,Example,Telemetry,telemetry,80,Approved,Manual,Remove\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert database.remove_domain("remove.example.com")

    content = csv_file.read_text(encoding="utf-8")

    assert content.startswith("Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes")
    assert "keep.example.com,Example,Telemetry,telemetry,90,Approved,Manual,Keep" in content
    assert "remove.example.com" not in content


def test_cli_add_search_remove_workflow(monkeypatch, tmp_path, capsys):

    csv_file = tmp_path / "domains.csv"
    csv_file.write_text(
        "Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert fivebr.main(
        [
            "add",
            "--domain",
            "test.example",
            "--vendor",
            "Example",
            "--category",
            "Telemetry",
            "--filter",
            "telemetry",
            "--confidence",
            "75",
        ]
    ) == 0

    assert "test.example,Example,Telemetry,telemetry,75,,," in csv_file.read_text(
        encoding="utf-8"
    )

    assert fivebr.main(["search", "test.example"]) == 0
    output = capsys.readouterr().out
    assert "Domain      : test.example" in output

    monkeypatch.setattr("builtins.input", lambda: "y")

    assert fivebr.main(["remove", "test.example"]) == 0
    assert "test.example" not in csv_file.read_text(encoding="utf-8")

    assert fivebr.main(["search", "test.example"]) == 1
    output = capsys.readouterr().out
    assert "Domain not found." in output


def test_add_interactive_prompts_are_rendered_once(monkeypatch, tmp_path, capsys):

    csv_file = tmp_path / "domains.csv"
    csv_file.write_text(
        "Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.stdin",
        StringIO("prompt.example\nExample\nTelemetry\ntelemetry\n75\n"),
    )

    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert fivebr.main(["add"]) == 0

    output = capsys.readouterr().out
    content = csv_file.read_text(encoding="utf-8")

    assert "Domain: Domain:" not in output
    assert "Vendor: Vendor:" not in output
    assert "Category: Category:" not in output
    assert "Filter: Filter:" not in output
    assert "Confidence: Confidence:" not in output
    assert output.count("Domain:") == 1
    assert output.count("Vendor:") == 1
    assert output.count("Category:") == 1
    assert output.count("Filter:") == 1
    assert output.count("Confidence:") == 1
    assert "prompt.example,Example,Telemetry,telemetry,75,,," in content


def test_cli_add_update_search_remove_interactive_workflow(monkeypatch, tmp_path, capsys):

    csv_file = tmp_path / "domains.csv"
    csv_file.write_text(
        "Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(database, "DATABASE", csv_file)
    monkeypatch.setattr(
        "sys.stdin",
        StringIO("test.example\nTest\nAds\nads\n100\n"),
    )

    assert fivebr.main(["add"]) == 0

    assert fivebr.main(["search", "test.example"]) == 0
    output = capsys.readouterr().out
    assert "Vendor      : Test" in output
    assert "Category    : Ads" in output
    assert "Filter      : ads" in output
    assert "Confidence  : 100" in output

    answers = iter(["test.example", "", "", "", "95"])
    monkeypatch.setattr("builtins.input", lambda: next(answers))

    assert fivebr.main(["update"]) == 0

    assert fivebr.main(["search", "test.example"]) == 0
    output = capsys.readouterr().out
    assert "Vendor      : Test" in output
    assert "Category    : Ads" in output
    assert "Filter      : ads" in output
    assert "Confidence  : 95" in output

    monkeypatch.setattr("builtins.input", lambda: "y")

    assert fivebr.main(["remove", "test.example"]) == 0

    assert fivebr.main(["search", "test.example"]) == 1
    output = capsys.readouterr().out
    assert "Domain not found." in output
