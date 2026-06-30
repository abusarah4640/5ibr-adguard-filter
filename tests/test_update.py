from scripts import database
import fivebr


def write_database(path):

    path.write_text(
        "Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes\n"
        "doubleclick.net,Google,Ads,ads,100,Approved,Google Ads,Advertising\n",
        encoding="utf-8",
    )


def read_database(path):

    return path.read_text(encoding="utf-8")


def test_update_vendor(monkeypatch, tmp_path):

    csv_file = tmp_path / "domains.csv"
    write_database(csv_file)
    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert fivebr.main(["update", "--domain", "doubleclick.net", "--vendor", "Google LLC"]) == 0

    content = read_database(csv_file)
    assert "doubleclick.net,Google LLC,Ads,ads,100,Approved,Google Ads,Advertising" in content


def test_update_category(monkeypatch, tmp_path):

    csv_file = tmp_path / "domains.csv"
    write_database(csv_file)
    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert fivebr.main(["update", "--domain", "doubleclick.net", "--category", "Privacy"]) == 0

    content = read_database(csv_file)
    assert "doubleclick.net,Google,Privacy,ads,100,Approved,Google Ads,Advertising" in content


def test_update_filter(monkeypatch, tmp_path):

    csv_file = tmp_path / "domains.csv"
    write_database(csv_file)
    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert fivebr.main(["update", "--domain", "doubleclick.net", "--filter", "privacy"]) == 0

    content = read_database(csv_file)
    assert "doubleclick.net,Google,Ads,privacy,100,Approved,Google Ads,Advertising" in content


def test_update_confidence(monkeypatch, tmp_path):

    csv_file = tmp_path / "domains.csv"
    write_database(csv_file)
    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert fivebr.main(["update", "--domain", "doubleclick.net", "--confidence", "95"]) == 0

    content = read_database(csv_file)
    assert "doubleclick.net,Google,Ads,ads,95,Approved,Google Ads,Advertising" in content


def test_partial_update_preserves_unspecified_values(monkeypatch, tmp_path):

    csv_file = tmp_path / "domains.csv"
    write_database(csv_file)
    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert fivebr.main(["update", "--domain", "doubleclick.net", "--confidence", "95"]) == 0

    content = read_database(csv_file)
    assert "doubleclick.net,Google,Ads,ads,95,Approved,Google Ads,Advertising" in content


def test_update_unknown_domain_returns_error(monkeypatch, tmp_path, capsys):

    csv_file = tmp_path / "domains.csv"
    write_database(csv_file)
    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert fivebr.main(["update", "--domain", "missing.example", "--confidence", "95"]) == 1

    output = capsys.readouterr().out
    assert "ERROR: Domain not found." in output


def test_update_invalid_confidence_returns_error(monkeypatch, tmp_path, capsys):

    csv_file = tmp_path / "domains.csv"
    write_database(csv_file)
    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert fivebr.main(["update", "--domain", "doubleclick.net", "--confidence", "101"]) == 1

    output = capsys.readouterr().out
    assert "ERROR: Confidence must be between 0 and 100." in output


def test_interactive_update_preserves_blank_values(monkeypatch, tmp_path, capsys):

    csv_file = tmp_path / "domains.csv"
    write_database(csv_file)
    monkeypatch.setattr(database, "DATABASE", csv_file)

    answers = iter(
        [
            "doubleclick.net",
            "",
            "Privacy",
            "",
            "95",
        ]
    )
    consumed = []

    def input_answer():
        answer = next(answers)
        consumed.append(answer)
        return answer

    monkeypatch.setattr("builtins.input", input_answer)

    assert fivebr.main(["update"]) == 0

    output = capsys.readouterr().out
    content = read_database(csv_file)

    assert "Current values" in output
    assert "Vendor [Google]:" in output
    assert "Category [Ads]:" in output
    assert "Filter [ads]:" in output
    assert "Confidence [100]:" in output
    assert "doubleclick.net,Google,Privacy,ads,95,Approved,Google Ads,Advertising" in content
    assert consumed == ["doubleclick.net", "", "Privacy", "", "95"]


def test_update_preserves_csv_metadata_columns(monkeypatch, tmp_path):

    csv_file = tmp_path / "domains.csv"
    write_database(csv_file)
    monkeypatch.setattr(database, "DATABASE", csv_file)

    assert fivebr.main(["update", "--domain", "doubleclick.net", "--confidence", "95"]) == 0

    lines = csv_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "Domain,Vendor,Category,Filter,Confidence,Status,Source,Notes"
    assert "doubleclick.net,Google,Ads,ads,95,Approved,Google Ads,Advertising" in lines


def test_add_search_update_search_remove_workflow(monkeypatch, tmp_path, capsys):

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
            "workflow.example",
            "--vendor",
            "Example",
            "--category",
            "Telemetry",
            "--filter",
            "telemetry",
            "--confidence",
            "80",
        ]
    ) == 0

    assert fivebr.main(["search", "workflow.example"]) == 0
    output = capsys.readouterr().out
    assert "Domain      : workflow.example" in output

    assert fivebr.main(["update", "--domain", "workflow.example", "--confidence", "95"]) == 0

    assert fivebr.main(["search", "workflow.example"]) == 0
    output = capsys.readouterr().out
    assert "Confidence  : 95" in output

    monkeypatch.setattr("builtins.input", lambda: "y")
    assert fivebr.main(["remove", "workflow.example"]) == 0

    assert fivebr.main(["search", "workflow.example"]) == 1
    output = capsys.readouterr().out
    assert "Domain not found." in output
