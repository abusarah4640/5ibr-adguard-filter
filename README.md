# 5ibr AdGuard Filter

قوائم فلترة مخصصة لـ AdGuard Home لمشروع 5ibr، مقسمة إلى إعلانات، تتبع/Telemetry، خصوصية، جوال، Smart TV، ألعاب، ومحتوى عائلي.

## القوائم الجاهزة للاستيراد

- `releases/home.txt` — مناسب لمعظم أجهزة البيت.
- `releases/privacy.txt` — خصوصية وتتبّع فقط.
- `releases/gaming.txt` — تتبع الألعاب فقط.
- `releases/family.txt` — فلتر عائلي متوازن.
- `releases/strict-family.txt` — فلتر عائلي أشد.
- `releases/all.txt` — كل التصنيفات في قائمة واحدة.

## التشغيل

```bash
python3 fivebr.py build
python3 fivebr.py validate
python3 fivebr.py stats
python3 fivebr.py report
```

## الإضافة والبحث

```bash
python3 fivebr.py search example.com
python3 fivebr.py add --domain example.com --vendor Example --category Telemetry --filter telemetry --confidence 90
python3 fivebr.py build
python3 fivebr.py validate
```

## ملاحظة

استخدم قائمة واحدة أساسية داخل AdGuard Home لتجنب التكرار. عند حدوث مشكلة في موقع أو لعبة، أضف الاستثناء في `filters/whitelist.txt` أو في Custom filtering rules داخل AdGuard Home.

## Architecture

```text
CSV Database
    ↓
CLI Commands / Builder
    ↓
Category Filter Files
    ↓
Release Bundles
```

The project is built around one source of truth: `database/domains.csv`.
CLI commands manage the database, the builder generates filter files from it, and release bundles combine filters into ready-to-use AdGuard Home lists.

## Phase 2 CLI Commands

```bash
python fivebr.py list --vendor Google --status Approved
python fivebr.py doctor
python fivebr.py normalize --dry-run
python fivebr.py export --format json --output database-export.json
python fivebr.py import new-domains.csv --status Pending
```

- `list`: shows database rows with filtering by vendor, category, filter, or status.
- `doctor`: checks database, config, filters, releases, duplicates, and confidence values.
- `normalize`: cleans casing, whitespace, domain formatting, and common vendor/category/status aliases.
- `export`: exports the database to CSV, JSON, or Markdown.
- `import`: imports CSV/JSON rows and defaults new items to `Pending` for review.

## Review Workflow

```text
New Domain
    ↓
Pending
    ↓
Review
    ↓
Approved
    ↓
Build / Release
```

New imported domains should enter the database as `Pending`. Reviewers can validate the source, category, filter, confidence, and safety impact before changing the status to `Approved`.


## Phase 3 Platform Hardening

The project now includes a Services layer:

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
```

Key Phase 3 additions:

- Central Database Integrity validation.
- Metadata support: Created, Updated, Reviewer, Source, Evidence and Notes.
- Review Workflow: Pending → Approved → Build.
- Database reports for status, vendors and categories.

Review commands:

```bash
python fivebr.py review submit --domain example.com --vendor Example --category Telemetry --filter telemetry --confidence 80
python fivebr.py review pending
python fivebr.py review approve example.com --reviewer ibrahim
python fivebr.py review reject example.com --reviewer ibrahim --notes "Insufficient evidence"
```

## Phase 4 - Project Stabilization

Phase 4 focuses on stabilizing the project as an open-source product rather than adding more runtime features.

Documentation map:

```text
README.md
    ↓
PROJECT_MASTER_CONTEXT.md
    ↓
docs/
    ├── specs/
    ├── adr/
    └── releases/
```

Stabilization documents:

- `docs/specs/cli-spec.md`
- `docs/specs/csv-schema.md`
- `docs/specs/filter-format.md`
- `docs/specs/review-workflow.md`
- `docs/adr/ADR-001-csv-instead-of-sqlite.md`
- `docs/adr/ADR-002-command-registry.md`
- `docs/adr/ADR-003-services-layer.md`
- `docs/adr/ADR-004-metadata-preservation.md`
- `docs/releases/v1.0.0-beta.md`

Current stabilization target: `v1.0.0-beta`.
