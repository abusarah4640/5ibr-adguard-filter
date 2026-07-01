# ADR-004: Metadata Preservation

Status: Accepted

## Context

5ibr AdGuard Filter Toolkit is evolving from a script collection into an open-source database and release toolkit.

## Decision

Database writes must preserve unknown CSV columns. This protects compatibility with future metadata, community workflows and external tooling.

## Consequences

- The project remains simple to contribute to.
- Architecture decisions are documented instead of being hidden in code history.
- Future changes must either follow this decision or add a new ADR that supersedes it.
