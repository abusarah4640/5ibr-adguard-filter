from pathlib import Path

from scripts import doctor, export_cmd, list_cmd, normalize


def test_list_command_supports_limit(capsys):
    assert list_cmd.main(["--limit", "2"]) == 0
    output = capsys.readouterr().out
    assert "Rows: 2" in output
    assert "Domain" in output


def test_doctor_passes_current_project(capsys):
    assert doctor.main([]) == 0
    output = capsys.readouterr().out
    assert "Doctor PASSED" in output


def test_normalize_dry_run_does_not_fail(capsys):
    assert normalize.main(["--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "Dry run" in output


def test_export_markdown_to_file(tmp_path):
    output = tmp_path / "domains.md"
    assert export_cmd.main(["--format", "md", "--output", str(output)]) == 0
    text = output.read_text(encoding="utf-8")
    assert "| Domain |" in text
