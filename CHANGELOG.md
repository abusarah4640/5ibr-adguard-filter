# Changelog

## [2.2.0rc1] - Unreleased

### Candidate status

- Unified runtime, CLI, and Python package metadata on `2.2.0rc1`.
- Maintainer qualification completed with 709 automated tests.
- Python 3.11 through 3.14 and installed-Wheel CI qualification passed.
- Independent technical review remains pending.
- PR #9 remains Draft; no merge, tag, or public release is authorized.
- Release status remains NOT READY.

### Security and recovery

- Required authentication, RBAC, and CSRF protection for sensitive Web routes.
- Added session rotation, session revocation, and persistent login throttling.
- Required production secrets and trusted hosts and enabled Secure cookies.
- Confined Gunicorn to loopback behind Cloudflare Access.
- Removed public IPv4 and IPv6 access to port 8089.
- Completed and documented a production deployment and rollback drill.

### Build and validation

- Added staged atomic builds with validation before promotion and rollback.
- Added strict runtime artifact, filter-rule, CSV, and release validation.
- Added database-to-filter coherence and deterministic SHA-256 build tests.
- Locked Python dependencies and pinned GitHub Actions immutably.

## [2.0.0] - 2026-07-17

### Added
- Complete guardrail readiness governance flow: evaluation, dashboard visibility, diagnostics, progress, history and trends.
- Explainable readiness decision engine with stability-window rules.
- Manual approval gate with reviewer confirmation and decision fingerprinting.
- Append-only readiness decision and approval audit archive.

### Safety
- Enforcement remains disabled and is never activated automatically by the readiness workflow.

## [1.9.0] - 2026-07-15

### Added

- Runtime project architecture based on `FIVEBR_HOME`.
- Safe project initialization using packaged seed resources.
- Runtime project lifecycle states:
  - `PROJECT_INITIALIZED`
  - `PROJECT_OPERATIONAL`
  - `PROJECT_INVALID`
- `fivebr init` command.
- `fivebr project-status` command.
- Runtime architecture closure and release acceptance gates.
- Installed-Wheel runtime validation.
- Runtime-isolated Web UI support.
- Runtime-isolated audit, backup and suggestions services.
- Runtime-aware analyzer configuration.
- Runtime-aware Validate and Build workflows.
- Final package and release safety contracts.

### Changed

- Separated immutable application code from mutable runtime state.
- Centralized runtime paths through `scripts.runtime.paths`.
- Centralized version resolution through `scripts.version`.
- Updated Web CLI execution to use `python -m fivebr`.
- Updated builders to write only inside the active runtime.
- Updated Analyzer, Validate, Audit, Backup and Suggestions services to honor `FIVEBR_HOME`.
- Updated release metadata from prerelease `1.9.0rc3` to final `1.9.0`.

### Fixed

- Fixed installed-Wheel Web failures caused by source-relative paths.
- Fixed Analyzer configuration fallback to the process working directory.
- Fixed Validate reading configuration from `site-packages/config`.
- Fixed builders writing generated files into the source project.
- Fixed Web audit and backup services writing outside the active runtime.
- Fixed Suggestions and review decisions ignoring `FIVEBR_HOME`.
- Preserved compatibility with existing monkeypatched path constants in tests.
- Fixed Intelligence Report displaying `Version: unknown`.

### Validation

- 422 automated tests passed.
- Final version contract passed.
- Production verification passed.
- Installed-Wheel CLI acceptance passed.
- Installed-Wheel Web acceptance passed.
- Ten core Web routes returned HTTP 200.
- Mutable-service runtime isolation passed.
- RC3 live validation service passed restart and stability testing.
- Production service remained active and unchanged.

### Release Safety

The published package does not contain:

- Production policy files.
- Production database rows.
- Audit logs.
- Suggestion decisions.
- Runtime reports.
- Runtime backups.
- Mutable production state.

## [1.9.0rc2] - 2026-07-14

### Fixed

- Fixed installed Web UI runtime resolution when Gunicorn starts outside the source tree.
- `analyzer_service.load_analyzer_config()` now prioritizes `FIVEBR_HOME/config/analyzer.json`.
- Added `config/analyzer.json` to safe packaged seed resources.
- Newly initialized projects now include Analyzer configuration and can run Web UI independently.

### Verification

- Added regression coverage for Analyzer runtime-path resolution.
- Added seed-runtime tests for initialized Analyzer configuration.
- Verified production remains `PRODUCTION_VERIFIED`.
- 408 automated tests passing before RC2 packaging.

## [1.9.0rc1] - 2026-07-13

### Added

- Production lifecycle with formal status, verification, guarded disable, guarded re-enable, audit receipts, rollback protection, and lifecycle acceptance gates.
- Runtime resource architecture supporting source checkouts and installed Wheels through `FIVEBR_HOME`.
- Safe `fivebr init` command for creating isolated runtime projects from packaged seed resources.
- Project lifecycle states:
  - `PROJECT_INITIALIZED`
  - `PROJECT_OPERATIONAL`
  - `PROJECT_INVALID`
- `fivebr project-status` with human-readable and JSON output.
- Lifecycle-aware `fivebr doctor` behavior for initialized, operational, and invalid projects.
- `fivebr version` with source-tree and installed-package version resolution.
- Runtime architecture closure audit and machine-readable acceptance reports.
- Isolated Wheel installation and acceptance testing.

### Changed

- Unified runtime and Python package version metadata at `1.9.0rc1`.
- Centralized runtime path resolution under `scripts.runtime.paths`.
- Migrated database and Doctor consumers to the central runtime path model.
- Added `scripts.operations`, `scripts.runtime`, and `scripts.runtime.seeds` to package metadata.
- Strengthened package safety checks to exclude production enforcement policies, reports, audit logs, and backups from release artifacts.

### Safety and Production

- Production enforcement remains enabled for exactly 13 authorized domains.
- Policy SHA-256 verification remains active.
- Production audit integrity remains passing.
- Runtime seed resources contain no production policies or production data.
- New runtime projects are initialized with an empty database schema and safe configuration/filter defaults only.

### Verification

- 398 automated tests passing.
- Wheel metadata verified as `fivebr 1.9.0rc1`.
- Clean virtual-environment installation verified.
- `fivebr init`, `fivebr project-status`, and `fivebr doctor` verified from the installed Wheel.
- Production verification result: `PRODUCTION_VERIFIED`.

## v1.5.0 - Admin Platform Stabilization

### Added
- Database-driven dropdowns/datalists for vendors, categories, and filters in the Web UI.
- Safer suggestion approval form with editable values before approval.
- Template validation coverage to prevent broken Jinja templates.

### Fixed
- Broken Jinja expressions in Domains, Domain Form, Suggestions, Suggestion Form, and Audit templates.
- Add Domain route mismatch by standardizing on `/domains/add`.
- Domain filters now use exact values from the database instead of placeholder text.

### Safety
- Upgrade guide continues to preserve `database/domains.csv`, `config/analyzer.json`, `reports/`, `data/`, and `releases/`.


## v1.4.0 - Arabic Web UI Support

### Added
- Arabic/English language switch in the Web UI.
- RTL layout support for Arabic.
- Local translation helper without external services.
- Arabic labels for Dashboard, Domains, Suggestions, Analyze, Analyze Log, Releases, and Audit.

### Changed
- Dashboard and navigation now use translated labels.
- Web pages preserve code/domain display in left-to-right direction for readability.

### Notes
- No database schema changes.
- No changes to analyzer rules.
- No changes to releases or reports format.


## v1.2.0 Web Admin

### Added
- Web Suggestions review page with Approve/Edit and Reject actions.
- Web Audit Log for administrative actions.
- Automatic backups before Web UI write operations.
- Dashboard cards for approved/pending domains, suggestions and recent activity.

### Safety
- Write actions create timestamped backups under `data/backups/`.
- Web actions are logged under `data/audit/web-audit.csv`.


## v1.2.0 - Web Admin UI

- Added `fivebr-web` Flask admin interface.
- Added browser-based domain list, search, add, edit and delete workflows.
- Added web actions for doctor, validate and build.
- Added domain analyzer and query log analyzer pages.
- Added release file browser/download routes.

# Changelog

## v1.1.0 - Analyze Log

- Added `fivebr analyze-log PATH` for AdGuard Home query log analysis.
- Added `scripts/services/querylog_service.py` to parse query logs, count domains, skip known database entries, and reuse the existing analyzer service.
- Added automatic `reports/suggestions.csv` and `reports/suggestions.md` generation.
- Added `--min-seen` and `--limit` options for large query logs.
- Added query log analysis tests.


## Phase 5 - Domain Analyzer

- Added `fivebr analyze DOMAIN` for local rule-based domain analysis.
- Added `config/analyzer.json` with vendor patterns, category keywords, and filter mapping.
- Added `scripts/services/analyzer_service.py` without network calls or AI dependencies.
- Added analyzer tests for Microsoft telemetry, Google ads, Meta social, unknown domains, and database similarity.


## v1.0.0

### Added

- Initial project structure.
- Created custom filter project.
- First release based on AdGuard Home DNS logs.
## Phase 2 CLI Foundation

- Added `fivebr list` with vendor/category/filter/status filters.
- Added `fivebr doctor` project health checks.
- Added `fivebr normalize` with dry-run support.
- Added `fivebr export` for CSV, JSON and Markdown.
- Added `fivebr import` for CSV/JSON imports with default Pending status.
- Updated README architecture and review workflow sections.
- Reworked ROADMAP into Completed / In Progress / Planned / Backlog.

## Phase 3 - Platform Hardening

- Added `scripts/services/` as a reusable business-logic layer for CLI, future REST API and future Web UI.
- Added centralized database integrity validation in `integrity_service.py`.
- Added metadata-aware database operations in `database_service.py`.
- Added Review Workflow through `fivebr review`:
  - `submit`
  - `pending`
  - `approve`
  - `reject`
- Added standard metadata fields support: `Created`, `Updated`, `Reviewer`, `Source`, `Evidence`, `Notes`.
- Updated `doctor` to use the central integrity layer.
- Added database reports: status, vendor, category and database summary.
- Added Phase 3 tests for integrity and review workflow.

## v1.0.0-beta - Phase 4 Project Stabilization

### Added

- Added formal specs under `docs/specs/`:
  - CLI specification.
  - CSV schema specification.
  - Filter format specification.
  - Review workflow specification.
- Added Architecture Decision Records under `docs/adr/`:
  - ADR-001 CSV instead of SQLite.
  - ADR-002 Command Registry.
  - ADR-003 Services Layer.
  - ADR-004 Metadata Preservation.
- Added release notes under `docs/releases/v1.0.0-beta.md`.
- Upgraded `PROJECT_MASTER_CONTEXT.md` into a project dashboard.
- Updated `ROADMAP.md` for Phase 4 stabilization and post-v1.0 planning.

### Changed

- Set project version target to `1.0.0-beta`.
- Clarified documentation hierarchy and release readiness checklist.

### Notes

- No runtime feature expansion in this phase.
- No Services, Review Workflow or Database Integrity changes were introduced.

## v1.3.0 - Web Admin Daily Operations

### Added
- Audit Log page in the Web UI.
- Version display on the dashboard.
- Release file metadata with size and last modified time.
- Domain filters by vendor, category, filter, and status.
- Analyze shortcut from the Domains table.

### Improved
- Dashboard health card now reflects core project readiness.
- Navigation now includes Suggestions and Audit pages.
- Releases page now supports quick rebuild and file metadata.
