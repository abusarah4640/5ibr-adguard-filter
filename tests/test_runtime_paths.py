from pathlib import Path

from scripts.runtime.paths import (
    FIVEBR_HOME_ENV,
    PACKAGE_ROOT,
    get_runtime_paths,
    resolve_runtime_root,
)


def test_explicit_root_builds_all_paths(
    tmp_path,
):
    paths = get_runtime_paths(
        tmp_path
    )

    assert paths.root == tmp_path.resolve()
    assert (
        paths.config
        == tmp_path.resolve() / "config"
    )
    assert (
        paths.database
        == tmp_path.resolve() / "database"
    )
    assert (
        paths.filters
        == tmp_path.resolve() / "filters"
    )
    assert (
        paths.releases
        == tmp_path.resolve() / "releases"
    )
    assert (
        paths.reports
        == tmp_path.resolve() / "reports"
    )
    assert (
        paths.data
        == tmp_path.resolve() / "data"
    )
    assert (
        paths.version_file
        == tmp_path.resolve() / "VERSION"
    )


def test_environment_runtime_root(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv(
        FIVEBR_HOME_ENV,
        str(tmp_path),
    )

    assert (
        resolve_runtime_root()
        == tmp_path.resolve()
    )


def test_environment_root_has_priority(
    tmp_path,
    monkeypatch,
):
    custom = tmp_path / "custom-home"

    monkeypatch.setenv(
        FIVEBR_HOME_ENV,
        str(custom),
    )

    assert (
        resolve_runtime_root()
        == custom.resolve()
    )


def test_empty_environment_is_ignored(
    monkeypatch,
):
    monkeypatch.setenv(
        FIVEBR_HOME_ENV,
        "   ",
    )

    assert (
        resolve_runtime_root()
        == PACKAGE_ROOT
    )


def test_runtime_paths_do_not_create_files(
    tmp_path,
):
    root = tmp_path / "does-not-exist"

    paths = get_runtime_paths(root)

    assert paths.root == root.resolve()
    assert not root.exists()


def test_package_root_is_absolute():
    assert PACKAGE_ROOT.is_absolute()
