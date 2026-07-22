#!/usr/bin/env python3

"""Validate runtime configuration, filters and generated releases."""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from scripts.builders.releases import HEADER
from scripts.cli import parse_no_args
from scripts.runtime.paths import RuntimePaths, get_runtime_paths


def read_strict_text(path: Path) -> str:
    """Read one regular non-symlink file as strict UTF-8."""

    if path.is_symlink():
        raise ValueError("symbolic links are not allowed")
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise ValueError("not a regular file")

    return path.read_text(
        encoding="utf-8",
        errors="strict",
    )


def load_json_file(path: Path) -> Any:
    """Load strict UTF-8 JSON from a regular file."""

    return json.loads(read_strict_text(path))


def validate_config_files(
    paths: RuntimePaths,
) -> list[str]:
    """Validate every runtime JSON configuration file."""

    errors: list[str] = []

    if paths.config.is_symlink():
        return ["config: symbolic directories are not allowed"]

    if not paths.config.is_dir():
        return ["config: directory not found"]

    for path in sorted(paths.config.glob("*.json")):
        try:
            load_json_file(path)
        except (
            FileNotFoundError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
        ) as exc:
            errors.append(f"config/{path.name}: {exc}")

    return errors


def load_release_definitions(
    paths: RuntimePaths,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Load and structurally validate releases.json."""

    path = paths.config / "releases.json"
    errors: list[str] = []

    try:
        data = load_json_file(path)
    except (
        FileNotFoundError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        return {}, [f"config/releases.json: {exc}"]

    if not isinstance(data, dict):
        return {}, ["config/releases.json: root must be an object"]

    releases: dict[str, dict[str, Any]] = {}

    for name, release in data.items():
        prefix = f"config/releases.json:{name}"

        if (
            not isinstance(name, str)
            or not name
            or Path(name).name != name
        ):
            errors.append(f"{prefix}: invalid release name")
            continue

        if not isinstance(release, dict):
            errors.append(f"{prefix}: release must be an object")
            continue

        title = release.get("title")
        description = release.get("description")
        filters = release.get("filters")

        if not isinstance(title, str) or not title.strip():
            errors.append(f"{prefix}: title must be a non-empty string")

        if not isinstance(description, str):
            errors.append(f"{prefix}: description must be a string")

        if (
            not isinstance(filters, list)
            or not filters
            or not all(
                isinstance(item, str)
                and item
                and Path(item).name == item
                for item in filters
            )
        ):
            errors.append(
                f"{prefix}: filters must be non-empty safe names"
            )
            continue

        if len(filters) != len(set(filters)):
            errors.append(f"{prefix}: duplicate filter reference")

        releases[name] = release

    return releases, errors


def load_filter_files(
    paths: RuntimePaths,
    releases: dict[str, dict[str, Any]],
) -> dict[str, Path]:
    """Return every actual or release-referenced filter file."""

    files = {
        path.stem: path
        for path in paths.filters.glob("*.txt")
    }

    for release in releases.values():
        for name in release["filters"]:
            files.setdefault(
                name,
                paths.filters / f"{name}.txt",
            )

    return dict(sorted(files.items()))


DOMAIN_LABEL = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
)


def validate_domain_name(domain: str) -> str | None:
    """Return an error for an invalid DNS domain, otherwise None."""

    if domain != domain.strip():
        return "leading or trailing whitespace is not allowed"
    if domain != domain.lower():
        return "domain must be lowercase"
    if domain.endswith("."):
        return "trailing root dots are not allowed"

    try:
        ascii_domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        return "domain is not valid IDNA"

    if len(ascii_domain) > 253:
        return "domain exceeds 253 bytes"

    labels = ascii_domain.split(".")
    if len(labels) < 2:
        return "domain must contain at least two labels"
    if labels[-1].isdigit():
        return "top-level label must not be numeric"

    for label in labels:
        if not label:
            return "empty domain labels are not allowed"
        if len(label) > 63:
            return "domain label exceeds 63 bytes"
        if DOMAIN_LABEL.fullmatch(label) is None:
            return f"invalid domain label: {label}"

    return None


def validate_filter_rule(
    filename: str,
    line: str,
) -> str | None:
    """Validate one supported filter rule."""

    if filename == "whitelist.txt":
        match = re.fullmatch(r"@@\|\|(.+)\^", line)
        if match is None:
            return "whitelist rules must use @@||domain^ syntax"
        domain = match.group(1)
    else:
        if line.startswith("@@"):
            return "exception rules are only allowed in whitelist.txt"
        domain = line

    domain_error = validate_domain_name(domain)
    if domain_error:
        return f"invalid domain {domain!r}: {domain_error}"

    return None


def validate_filters(
    paths: RuntimePaths,
    releases: dict[str, dict[str, Any]],
) -> tuple[dict[str, str], list[str], int, int]:
    """Validate strict filter files and duplicate rules."""

    errors: list[str] = []
    contents: dict[str, str] = {}
    global_rules: dict[str, str] = {}
    total_rules = 0

    if paths.filters.is_symlink():
        return (
            contents,
            ["filters: symbolic directories are not allowed"],
            0,
            0,
        )

    if not paths.filters.is_dir():
        return contents, ["filters: directory not found"], 0, 0

    for name, path in load_filter_files(paths, releases).items():
        filename = path.name
        print(f"Checking {filename}")

        try:
            text = read_strict_text(path)
        except (
            FileNotFoundError,
            UnicodeDecodeError,
            ValueError,
        ) as exc:
            print(f"  ERROR : {exc}")
            errors.append(f"filters/{filename}: {exc}")
            print()
            continue

        if "\x00" in text:
            message = "NUL bytes are not allowed"
            print(f"  ERROR : {message}")
            errors.append(f"filters/{filename}: {message}")
            print()
            continue

        contents[name] = text
        rules: set[str] = set()

        for number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            line = line.strip()

            if not line or line.startswith("!"):
                continue

            total_rules += 1

            rule_error = validate_filter_rule(
                filename,
                line,
            )
            if rule_error:
                print(
                    f"  ERROR : line {number}: {rule_error}"
                )
                errors.append(
                    f"filters/{filename}:{number}: "
                    f"{rule_error}"
                )
                continue

            if line in rules:
                print(
                    f"  Duplicate in file : line {number}"
                )
                errors.append(
                    f"filters/{filename}:{number}: "
                    "duplicate rule in file"
                )

            rules.add(line)

            if line in global_rules:
                other = global_rules[line]
                print(
                    f"  Duplicate across files : "
                    f"{filename} ↔ {other}"
                )
                errors.append(
                    f"filters/{filename}:{number}: "
                    f"duplicate rule from {other}"
                )
            else:
                global_rules[line] = filename

        print(f"  OK ({len(rules)} rules)")
        print()

    return contents, errors, len(global_rules), total_rules


def expected_release_text(
    name: str,
    release: dict[str, Any],
    filter_contents: dict[str, str],
) -> str | None:
    """Build the exact expected release text from validated filters."""

    filters = release["filters"]

    if any(filter_name not in filter_contents for filter_name in filters):
        return None

    output = [
        HEADER.format(
            title=release.get("title", name),
            description=release.get("description", ""),
        )
    ]

    for filter_name in filters:
        output.append(
            f"! ===== {filter_name.upper()} ====="
        )
        output.append(filter_contents[filter_name])

    return "\n".join(output)


def validate_releases(
    paths: RuntimePaths,
    releases: dict[str, dict[str, Any]],
    filter_contents: dict[str, str],
) -> list[str]:
    """Validate generated release names, encoding and exact contents."""

    errors: list[str] = []

    if paths.releases.is_symlink():
        return ["releases: symbolic directories are not allowed"]

    if not paths.releases.is_dir():
        return ["releases: directory not found"]

    expected_names = {
        f"{name}.txt"
        for name in releases
    }
    actual_paths = {
        path.name: path
        for path in paths.releases.glob("*.txt")
    }

    for extra in sorted(set(actual_paths) - expected_names):
        errors.append(f"releases/{extra}: unexpected stale release")

    for filename in sorted(expected_names):
        path = paths.releases / filename

        try:
            actual = read_strict_text(path)
        except (
            FileNotFoundError,
            UnicodeDecodeError,
            ValueError,
        ) as exc:
            errors.append(f"releases/{filename}: {exc}")
            continue

        name = path.stem
        expected = expected_release_text(
            name,
            releases[name],
            filter_contents,
        )

        if expected is None:
            errors.append(
                f"releases/{filename}: "
                "cannot verify because a filter is invalid or missing"
            )
        elif actual != expected:
            errors.append(
                f"releases/{filename}: "
                "content does not match configured filters"
            )

    return errors


REQUIRED_DATABASE_FIELDS = (
    "Domain",
    "Vendor",
    "Category",
    "Filter",
    "Confidence",
    "Status",
)
VALID_DATABASE_STATUSES = {
    "Pending",
    "Approved",
    "Rejected",
}


def validate_database(
    paths: RuntimePaths,
    filter_contents: dict[str, str],
) -> list[str]:
    """Validate the runtime CSV and its approved filter outputs."""

    errors: list[str] = []
    database_path = paths.database / "domains.csv"

    if paths.database.is_symlink():
        return [
            "database: symbolic directories are not allowed"
        ]
    if not paths.database.is_dir():
        return ["database: directory not found"]

    try:
        text = read_strict_text(database_path)
    except (
        FileNotFoundError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        return [f"database/domains.csv: {exc}"]

    if "\x00" in text:
        return [
            "database/domains.csv: NUL bytes are not allowed"
        ]

    try:
        reader = csv.DictReader(
            io.StringIO(text, newline=""),
            strict=True,
        )
        fieldnames = reader.fieldnames
        if fieldnames is None:
            return ["database/domains.csv: missing CSV header"]

        if any(not field for field in fieldnames):
            errors.append(
                "database/domains.csv: empty header fields "
                "are not allowed"
            )

        duplicates = sorted({
            field
            for field in fieldnames
            if fieldnames.count(field) > 1
        })
        if duplicates:
            errors.append(
                "database/domains.csv: duplicate header fields: "
                + ", ".join(duplicates)
            )

        missing = [
            field
            for field in REQUIRED_DATABASE_FIELDS
            if field not in fieldnames
        ]
        if missing:
            errors.append(
                "database/domains.csv: missing required fields: "
                + ", ".join(missing)
            )
            return errors

        try:
            categories_data = load_json_file(
                paths.config / "categories.json"
            )
        except (
            OSError,
            ValueError,
        ):
            categories_data = {}

        categories = (
            {
                str(name).strip().replace("-", " ").lower()
                for name in categories_data
            }
            if isinstance(categories_data, dict)
            else set()
        )

        expected: dict[str, set[str]] = {}
        seen_domains: dict[str, int] = {}

        for row_number, row in enumerate(reader, start=2):
            if None in row:
                errors.append(
                    f"database/domains.csv:{row_number}: "
                    "row has values beyond the CSV header"
                )
                continue

            values = {
                field: (row.get(field) or "").strip()
                for field in REQUIRED_DATABASE_FIELDS
            }
            domain = values["Domain"]
            vendor = values["Vendor"]
            category = values["Category"]
            filter_name = values["Filter"]
            confidence_raw = values["Confidence"]
            status = values["Status"]

            domain_error = validate_domain_name(domain)
            if domain_error:
                errors.append(
                    f"database/domains.csv:{row_number}: "
                    f"invalid domain {domain!r}: {domain_error}"
                )
            else:
                seen_domains[domain] = (
                    seen_domains.get(domain, 0) + 1
                )

            if not vendor:
                errors.append(
                    f"database/domains.csv:{row_number}: "
                    "vendor is required"
                )

            if not category:
                errors.append(
                    f"database/domains.csv:{row_number}: "
                    "category is required"
                )
            elif (
                categories
                and category.replace("-", " ").lower()
                not in categories
            ):
                errors.append(
                    f"database/domains.csv:{row_number}: "
                    f"unknown category: {category}"
                )

            if not filter_name:
                errors.append(
                    f"database/domains.csv:{row_number}: "
                    "filter is required"
                )
            elif filter_name not in filter_contents:
                errors.append(
                    f"database/domains.csv:{row_number}: "
                    f"unknown filter: {filter_name}"
                )

            try:
                confidence = int(confidence_raw)
            except ValueError:
                errors.append(
                    f"database/domains.csv:{row_number}: "
                    f"invalid confidence: {confidence_raw!r}"
                )
            else:
                if confidence < 0 or confidence > 100:
                    errors.append(
                        f"database/domains.csv:{row_number}: "
                        f"confidence out of range: {confidence}"
                    )

            if status not in VALID_DATABASE_STATUSES:
                errors.append(
                    f"database/domains.csv:{row_number}: "
                    f"invalid status: {status!r}"
                )

            if (
                status == "Approved"
                and domain_error is None
                and filter_name in filter_contents
            ):
                expected.setdefault(
                    filter_name,
                    set(),
                ).add(domain)

    except csv.Error as exc:
        errors.append(
            f"database/domains.csv: malformed CSV: {exc}"
        )
        return errors

    for domain, count in sorted(seen_domains.items()):
        if count > 1:
            errors.append(
                "database/domains.csv: duplicate domain: "
                f"{domain} ({count} rows)"
            )

    actual: dict[str, set[str]] = {}
    for filter_name, filter_text in filter_contents.items():
        if filter_name == "whitelist":
            continue
        actual[filter_name] = {
            line.strip()
            for line in filter_text.splitlines()
            if line.strip()
            and not line.strip().startswith("!")
        }

    for filter_name in sorted(set(expected) | set(actual)):
        expected_rules = expected.get(filter_name, set())
        actual_rules = actual.get(filter_name, set())

        for domain in sorted(expected_rules - actual_rules):
            errors.append(
                f"filters/{filter_name}.txt: "
                f"missing approved domain: {domain}"
            )

        for domain in sorted(actual_rules - expected_rules):
            errors.append(
                f"filters/{filter_name}.txt: "
                f"domain is not approved in database: {domain}"
            )

    return errors


def validate_runtime(
    root: str | Path | None = None,
) -> list[str]:
    """Validate one complete runtime tree and return all errors."""

    paths = get_runtime_paths(root)
    errors = validate_config_files(paths)

    releases, release_errors = load_release_definitions(paths)
    errors.extend(release_errors)

    (
        filter_contents,
        filter_errors,
        unique_rules,
        total_rules,
    ) = validate_filters(paths, releases)

    errors.extend(filter_errors)
    errors.extend(
        validate_database(
            paths,
            filter_contents,
        )
    )
    errors.extend(
        validate_releases(
            paths,
            releases,
            filter_contents,
        )
    )

    print("------------------------------------------")
    print(f"Total unique rules : {unique_rules}")
    print(f"Total rules        : {total_rules}")
    print("------------------------------------------")

    return errors


def main(argv: list[str] | None = None) -> int:
    """Validate runtime configuration, filters and releases."""

    parse_no_args(
        prog="fivebr validate",
        description="Validate generated runtime artifacts",
        argv=argv,
    )

    print()
    print("==========================================")
    print("5ibr Runtime Validator")
    print("==========================================")
    print()

    try:
        errors = validate_runtime()
    except OSError as exc:
        errors = [f"runtime: {exc}"]

    if errors:
        print()
        print("Validation errors:")
        for error in errors:
            print(f"  ERROR : {error}")
        print()
        print("Validation FAILED")
        return 1

    print()
    print("Validation PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
