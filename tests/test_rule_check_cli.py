from scripts.rule_check import main, validate_rule_config


def test_validate_rule_config_success():
    ok, errors = validate_rule_config(
        {
            "vendor_patterns": {},
            "category_keywords": {},
            "filter_map": {},
        }
    )

    assert ok
    assert errors == []


def test_validate_rule_config_errors():
    ok, errors = validate_rule_config(
        {
            "vendor_patterns": [],
        }
    )

    assert not ok
    assert "section must be an object: vendor_patterns" in errors
    assert "missing required section: category_keywords" in errors
    assert "missing required section: filter_map" in errors


def test_rule_check_cli_success(capsys):
    exit_code = main([])

    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Rule config:" in output
    assert "Rule Config: OK" in output
