"""Version identity contract for the 2.2.0 release candidate."""

from pathlib import Path
import re
import tomllib

from scripts.version import get_version


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "2.2.0rc1"


def read_runtime_version() -> str:
    return (
        PROJECT_ROOT
        / "VERSION"
    ).read_text(encoding="utf-8").strip()


def read_package_version() -> str:
    with (
        PROJECT_ROOT
        / "pyproject.toml"
    ).open("rb") as handle:
        data = tomllib.load(handle)

    return data["project"]["version"]


def test_runtime_and_package_versions_match_candidate():
    assert read_runtime_version() == EXPECTED_VERSION
    assert read_package_version() == EXPECTED_VERSION
    assert read_runtime_version() == read_package_version()


def test_version_service_matches_candidate_contract():
    assert get_version() == EXPECTED_VERSION


def test_candidate_version_is_pep440_rc_form():
    assert re.fullmatch(
        r"\d+\.\d+\.\d+rc\d+",
        EXPECTED_VERSION,
    )


def test_candidate_is_not_advertised_as_final():
    assert EXPECTED_VERSION != "2.2.0"
    assert "rc" in EXPECTED_VERSION
