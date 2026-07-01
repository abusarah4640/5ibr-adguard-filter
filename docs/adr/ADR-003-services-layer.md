# ADR-003: Services Layer

Status: Accepted

## Context

5ibr AdGuard Filter Toolkit is evolving from a script collection into an open-source database and release toolkit.

## Decision

Reusable business logic belongs in `scripts/services/`. CLI commands should handle argument parsing and user interaction, then delegate domain logic to services. This prepares the project for future REST API or Web UI without rewriting core logic.

## Consequences

- The project remains simple to contribute to.
- Architecture decisions are documented instead of being hidden in code history.
- Future changes must either follow this decision or add a new ADR that supersedes it.
