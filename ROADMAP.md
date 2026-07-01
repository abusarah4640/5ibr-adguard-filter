# Roadmap

## Completed

### Phase 1 - CLI Refactor

- Structured project layout.
- Command registry based CLI.
- `fivebr.py` as a command router.
- CRUD foundation: add, search, update, remove.
- Build, validate, stats and report commands.
- Initial GitHub structure and tests.

### Phase 2 - Database Management

- `list`
- `doctor`
- `normalize`
- `export`
- `import`
- README architecture section.
- Roadmap structure.

### Phase 3 - Platform Hardening

- `scripts/services/` business logic layer.
- Central database integrity validation.
- Metadata-aware database operations.
- Review workflow: submit, pending, approve, reject.
- Reports for status, vendors and categories.
- Regression fix for interactive add workflow.

### Phase 4 - Project Stabilization

- Version target: `v1.0.0-beta`.
- Specs added under `docs/specs/`.
- Architecture Decision Records added under `docs/adr/`.
- Release notes added under `docs/releases/`.
- `PROJECT_MASTER_CONTEXT.md` upgraded into a project dashboard.

## In Progress

- Stabilization review before first beta release.
- Manual verification checklist.
- Documentation consistency review.

## Planned

### v1.0.0

- Final release notes.
- Git tag.
- GitHub Release artifact.
- Release checksum/signing plan.
- Coverage report.
- Stronger duplicate and vendor-alias reporting.

### Phase 5 - Community Platform

- Contributor review process.
- Community moderation roles.
- Pending queue policy.
- Public contribution templates for new domains.

### Phase 6 - Automation

- Automated release packaging.
- Changelog automation.
- Scheduled validation/report jobs.
- Optional backup/restore workflow.

### Phase 7 - Web Interface

- REST API.
- Web dashboard.
- Plugin system.

## Backlog

- `doctor --fix`.
- `backup` / `restore`.
- Advanced coverage reports.
- Public metrics dashboard.
- SQLite investigation, only if CSV becomes a real limitation.
