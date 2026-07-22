from pathlib import Path
import re
import tomllib

from scripts.version import (
    get_version,
)


PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)

EXPECTED_VERSION = "2.2.0"
EXPECTED_PACKAGE_VERSION = "2.0.1"


def read_runtime_version() -> str:
    return (
        PROJECT_ROOT
        / "VERSION"
    ).read_text(
        encoding="utf-8"
    ).strip()


def read_package_version() -> str:
    with (
        PROJECT_ROOT
        / "pyproject.toml"
    ).open("rb") as handle:
        data = tomllib.load(handle)

    return data["project"]["version"]


def test_runtime_version_is_final_release():
    assert (
        read_runtime_version()
        == EXPECTED_VERSION
    )


def test_package_metadata_is_final_release():
    assert (
        read_package_version()
        == EXPECTED_PACKAGE_VERSION
    )


def test_stage_runtime_does_not_publish_package_metadata():
    assert (
        read_runtime_version()
        != read_package_version()
    )
    assert read_package_version() == EXPECTED_PACKAGE_VERSION


def test_version_service_matches_release_contract():
    assert (
        get_version()
        == EXPECTED_VERSION
    )


def test_final_version_is_pep440_form():
    assert re.fullmatch(
        r"\d+\.\d+\.\d+",
        EXPECTED_VERSION,
    )


def test_stage_version_is_not_advertised_as_stable():
    assert re.fullmatch(
        r"\d+\.\d+\.\d+",
        EXPECTED_VERSION,
    )
    assert "stage" not in EXPECTED_VERSION
