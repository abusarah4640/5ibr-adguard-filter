import json
from pathlib import Path

from scripts.runtime.project_init import (
    initialize_project,
)
from scripts.services.analyzer_service import (
    load_analyzer_config,
)


def test_initialized_project_contains_analyzer_config(
    tmp_path,
):
    root = tmp_path / "project"

    initialize_project(root)

    path = (
        root
        / "config"
        / "analyzer.json"
    )

    assert path.is_file()

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    assert "vendor_patterns" in data
    assert "category_keywords" in data
    assert "filter_map" in data


def test_analyzer_loads_from_initialized_runtime(
    tmp_path,
    monkeypatch,
):
    root = tmp_path / "project"

    initialize_project(root)

    monkeypatch.setenv(
        "FIVEBR_HOME",
        str(root),
    )

    config = load_analyzer_config()

    expected = json.loads(
        (
            root
            / "config"
            / "analyzer.json"
        ).read_text(encoding="utf-8")
    )

    assert config == expected
