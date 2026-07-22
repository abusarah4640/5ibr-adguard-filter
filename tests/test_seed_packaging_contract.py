from pathlib import Path

import tomllib


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

PYPROJECT = (
    PROJECT_ROOT / "pyproject.toml"
)

SEED_ROOT = (
    PROJECT_ROOT
    / "scripts"
    / "runtime"
    / "seeds"
)


EXPECTED_SEED_FILES = {
    "__init__.py",
    "config/analyzer.json",
    "config/categories.json",
    "config/database.json",
    "config/releases.json",
    "config/signatures.json",
    "config/vendors.json",
    "database/domains.csv",
    "filters/ads.txt",
    "filters/adult.txt",
    "filters/gaming.txt",
    "filters/mobile.txt",
    "filters/privacy.txt",
    "filters/smart-tv.txt",
    "filters/social.txt",
    "filters/telemetry.txt",
    "filters/whitelist.txt",
}


FORBIDDEN_SEED_FILES = {
    (
        "config/"
        "scoped-promotion-enforcement.json"
    ),
    (
        "config/"
        "scoped-promotion-policies.json"
    ),
}


def load_pyproject() -> dict:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)


def seed_files() -> set[str]:
    return {
        path.relative_to(
            SEED_ROOT
        ).as_posix()
        for path in SEED_ROOT.rglob("*")
        if (
            path.is_file()
            and "__pycache__"
            not in path.parts
            and path.suffix != ".pyc"
        )
    }


def test_seed_package_is_registered():
    data = load_pyproject()

    packages = (
        data["tool"]
        ["setuptools"]
        ["packages"]
    )

    assert (
        "scripts.runtime.seeds"
        in packages
    )


def test_seed_package_data_is_registered():
    data = load_pyproject()

    package_data = (
        data["tool"]
        ["setuptools"]
        ["package-data"]
    )

    assert (
        package_data[
            "scripts.runtime.seeds"
        ]
        == [
            "config/*.json",
            "database/*.csv",
            "filters/*.txt",
        ]
    )


def test_seed_source_contract_is_exact():
    assert (
        seed_files()
        == EXPECTED_SEED_FILES
    )


def test_production_files_are_not_seeds():
    assert not (
        seed_files()
        & FORBIDDEN_SEED_FILES
    )
