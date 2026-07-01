# Changelog

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
