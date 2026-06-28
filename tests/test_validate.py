from pathlib import Path


def test_categories_exists():

    assert Path(
        "config/categories.json"
    ).exists()


def test_signatures_exists():

    assert Path(
        "config/signatures.json"
    ).exists()