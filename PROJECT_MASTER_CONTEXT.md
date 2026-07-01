# 5ibr AdGuard Filter Toolkit

## Master Project Context / Project Dashboard

Last updated: Phase 4 - Project Stabilization

## Current Status

| Field | Value |
| --- | --- |
| Project | 5ibr AdGuard Filter Toolkit |
| Current Version | v1.0.0-beta |
| Current Phase | Phase 4 - Project Stabilization |
| Release Status | Beta candidate |
| Source of Truth | `database/domains.csv` |
| CLI Entry | `fivebr.py` |
| Architecture | CLI → Services → Database → CSV |
| Current Milestone | Stabilize documentation, specs, ADR and release notes |
| Known Critical Issues | None after Phase 3 interactive add regression fix |
| Next Sprint | Release readiness checklist and v1.0.0 preparation |

## Verification Commands

```bash
pytest -q
python fivebr.py build
python fivebr.py validate
python fivebr.py doctor
```

## Architecture

```text
fivebr.py
    ↓
CLI Commands
    ↓
Services
    ↓
Database
    ↓
CSV
    ↓
Build System
    ↓
Filters
    ↓
Releases
```

## Project Goal

Build a professional open-source AdGuard Home filter toolkit based on a structured database instead of manually maintained text files.

The project is not only a blocklist. It is a small platform for:

- Domain database management.
- Filter generation.
- Validation.
- Reports.
- Review workflow.
- Release packaging.
- Community contribution readiness.

## Directory Structure

```text
fivebr.py
scripts/
    services/
database/
filters/
config/
releases/
reports/
tests/
docs/
    specs/
    adr/
    releases/
.github/
```

## Database Contract

Canonical database:

```text
database/domains.csv
```

Core columns:

```text
Domain
Vendor
Category
Filter
Confidence
Status
```

Standard metadata:

```text
Created
Updated
Reviewer
Source
Evidence
Notes
```

Important rule: unknown CSV columns must be preserved by all read/write operations.

## Stable CLI Commands

```bash
python fivebr.py build
python fivebr.py validate
python fivebr.py stats
python fivebr.py report
python fivebr.py search DOMAIN
python fivebr.py add
python fivebr.py update DOMAIN
python fivebr.py remove DOMAIN
python fivebr.py list
python fivebr.py doctor
python fivebr.py normalize
python fivebr.py export
python fivebr.py import
python fivebr.py review pending
```

## Review Workflow

```text
New Domain
    ↓
Pending
    ↓
Review
    ↓
Approved / Rejected
    ↓
Build / Release
```

Community submissions should enter as `Pending`. Reviewers verify vendor, category, filter, confidence, source and evidence before approval.

## Documentation Map

```text
README.md
    ↓
PROJECT_MASTER_CONTEXT.md
    ↓
docs/
    ├── filter-guidelines.md
    ├── review-workflow.md
    ├── rule-review-process.md
    ├── services-architecture.md
    ├── specs/
    │   ├── cli-spec.md
    │   ├── csv-schema.md
    │   ├── filter-format.md
    │   └── review-workflow.md
    ├── adr/
    │   ├── ADR-001-csv-instead-of-sqlite.md
    │   ├── ADR-002-command-registry.md
    │   ├── ADR-003-services-layer.md
    │   └── ADR-004-metadata-preservation.md
    └── releases/
        └── v1.0.0-beta.md
```

## ADR Index

- ADR-001: CSV instead of SQLite.
- ADR-002: Command Registry.
- ADR-003: Services Layer.
- ADR-004: Metadata Preservation.

## Specs Index

- CLI specification.
- CSV schema specification.
- Filter format specification.
- Review workflow specification.

## Development Rules

- Do not put business logic in `fivebr.py`.
- Keep CLI commands thin.
- Put reusable logic in `scripts/services/`.
- Preserve unknown database columns.
- Add tests for every behavior change.
- Run tests, build, validate and doctor before release.
- Avoid Web UI, REST API, plugin system and SQLite until the platform is stable.

## Phase History

| Phase | Name | Status |
| --- | --- | --- |
| Phase 1 | CLI Refactor | Done |
| Phase 2 | Database Management | Done |
| Phase 3 | Platform Hardening | Done |
| Phase 4 | Project Stabilization | Current |
| Phase 5 | Community Platform | Planned |
| Phase 6 | Automation | Planned |
| Phase 7 | Web Interface | Planned |

## Release Readiness Checklist

- [ ] All tests pass.
- [ ] Build completes.
- [ ] Validate passes.
- [ ] Doctor passes.
- [ ] Changelog updated.
- [ ] Release notes updated.
- [ ] Specs reviewed.
- [ ] ADR index reviewed.
- [ ] Git tag prepared.
- [ ] GitHub Release prepared.
