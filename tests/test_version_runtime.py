from importlib.metadata import (
    PackageNotFoundError,
)

import scripts.version as version_service


def test_get_version_prefers_version_file(
    tmp_path,
    monkeypatch,
):
    version_file = tmp_path / "VERSION"

    version_file.write_text(
        "1.9.0-stage60\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        version_service,
        "VERSION_FILE",
        version_file,
    )

    assert (
        version_service.get_version()
        == "1.9.0-stage60"
    )


def test_get_version_falls_back_to_metadata(
    tmp_path,
    monkeypatch,
):
    missing = tmp_path / "VERSION"

    monkeypatch.setattr(
        version_service,
        "VERSION_FILE",
        missing,
    )

    monkeypatch.setattr(
        version_service,
        "package_version",
        lambda name: "1.9.0.dev60",
    )

    assert (
        version_service.get_version()
        == "1.9.0.dev60"
    )


def test_get_version_returns_unknown(
    tmp_path,
    monkeypatch,
):
    missing = tmp_path / "VERSION"

    monkeypatch.setattr(
        version_service,
        "VERSION_FILE",
        missing,
    )

    def missing_package(name):
        raise PackageNotFoundError(name)

    monkeypatch.setattr(
        version_service,
        "package_version",
        missing_package,
    )

    assert (
        version_service.get_version()
        == "unknown"
    )


def test_set_version_rejects_empty_value(
    tmp_path,
    monkeypatch,
):
    version_file = tmp_path / "VERSION"

    monkeypatch.setattr(
        version_service,
        "VERSION_FILE",
        version_file,
    )

    try:
        version_service.set_version("   ")

    except ValueError:
        pass

    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_version_main_prints_version(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        version_service,
        "get_version",
        lambda: "1.9.0.dev60",
    )

    result = version_service.main([])

    captured = capsys.readouterr()

    assert result == 0
    assert (
        captured.out.strip()
        == "1.9.0.dev60"
    )
