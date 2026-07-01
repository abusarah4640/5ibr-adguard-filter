# ADR-001: CSV instead of SQLite

Status: Accepted

## Context

5ibr AdGuard Filter Toolkit is evolving from a script collection into an open-source database and release toolkit.

## Decision

The project starts as a lightweight open-source filter toolkit. CSV keeps the database easy to inspect, diff, review and edit in pull requests. SQLite may be considered later, but CSV remains the current source of truth.

## Consequences

- The project remains simple to contribute to.
- Architecture decisions are documented instead of being hidden in code history.
- Future changes must either follow this decision or add a new ADR that supersedes it.
