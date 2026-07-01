# 5ibr AdGuard Filter — Audit Review

Date: 2026-07-01

## Summary

- Source package was reviewed, validated and rebuilt.
- Python test suite: 26 tests passed.
- Original filter syntax validation: passed.
- Cleaned development artifacts from the deliverable: `.git`, `__pycache__`, `.pytest_cache`, `.vscode`.
- Added an `adult` category and generated `family`, `strict-family`, and `all` release profiles.

## Current structure

- `filters/`: modular source filter files.
- `releases/`: ready-to-import AdGuard Home lists.
- `database/domains.csv`: central domain database.
- `config/`: category, release, vendor and signature config.
- `scripts/`: CLI tools for build, validate, report, stats, search, add, remove and update.

## Rule counts

- Modular filter files: 9
- Release files: 6
- Total modular rules: 48
- Unique modular rules: 48
- Duplicate exact rules: 0
- Exact block/allow conflicts: 0

## Findings

1. The original project was technically valid and buildable.
2. No exact duplicate rules were found in the modular filter set after rebuild.
3. No exact conflict was found between block rules and allow rules after rebuild.
4. `family.txt` originally did not contain adult-content blocking; the reviewed version adds this category.
5. The ZIP originally included Git history and cache files, which are not needed for import or sharing.

## Recommended AdGuard Home usage

Use one primary release list:

- `releases/home.txt` for normal home protection.
- `releases/privacy.txt` for privacy/telemetry only.
- `releases/gaming.txt` for gaming telemetry only.
- `releases/family.txt` or `releases/strict-family.txt` for family devices.
- `releases/all.txt` for all categories.

Keep `filters/whitelist.txt` as a separate allowlist only when something breaks.

## Notes

This review checks syntax, duplicates, exact conflicts and project structure. It does not guarantee that every third-party service will keep the same domains forever.
