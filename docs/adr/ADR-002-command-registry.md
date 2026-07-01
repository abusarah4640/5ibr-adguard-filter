# ADR-002: Command Registry

Status: Accepted

## Context

5ibr AdGuard Filter Toolkit is evolving from a script collection into an open-source database and release toolkit.

## Decision

`fivebr.py` acts as a command router using a registry instead of a long conditional chain. This keeps command discovery centralized while each command remains isolated in `scripts/`.

## Consequences

- The project remains simple to contribute to.
- Architecture decisions are documented instead of being hidden in code history.
- Future changes must either follow this decision or add a new ADR that supersedes it.
