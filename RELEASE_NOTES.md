# 5ibr 2.2.0rc1 Release Candidate

Candidate date: 2026-07-22

## Status

```text
Version                    : 2.2.0rc1
Technical qualification    : PASS
Maintainer self-review     : COMPLETE
Independent review         : PENDING
Pull request                : #9 DRAFT
Merge authorization         : NO
Tag authorization           : NO
Public release authorization: NO
Release status              : NOT READY
```

This is a qualified release candidate, not a final release. It must not be merged, tagged, or published until the remaining review decision is recorded.

## Qualification evidence

- 709 automated tests passed on the recovery continuation branch.
- Python 3.11, 3.12, 3.13, and 3.14 CI passed.
- The installed Wheel was tested outside the source tree.
- Locked dependencies were installed with verified SHA-256 hashes.
- GitHub Actions were pinned to immutable revisions.
- Repeated builds produced identical SHA-256 output snapshots.
- Doctor, Validate, and Project Status passed against the active runtime.
- Installed Wheel validation and mutable-service isolation passed.

## Security and production recovery

- Sensitive Web routes require authentication and appropriate roles.
- State-changing forms use CSRF protection.
- Login failures are throttled persistently without trusting forwarded client addresses.
- Sessions rotate at authentication boundaries and are revoked after account changes.
- Query-log analysis is confined to the runtime upload directory.
- Production requires a stable secret and explicit trusted hosts.
- Session, remember, and language cookies use the required security attributes.
- Gunicorn listens on `127.0.0.1:8089` behind Cloudflare Access.
- Public IPv4 and IPv6 firewall access to port 8089 was removed.
- A production deployment and rollback drill was completed and documented.

## Build and runtime integrity

- Build outputs are generated in an isolated staging runtime.
- Staged outputs are validated before transactional promotion.
- Promotion failures restore every live output directory.
- Runtime JSON, CSV, filters, and releases use strict UTF-8 validation.
- Symbolic links, malformed CSV and JSON, stale releases, and tampered releases are rejected.
- Approved database rows and generated blocking filters must match in both directions.
- Filter rules accept only the supported DNS-domain and whitelist exception forms.

## Runtime workflow

```bash
fivebr init /path/to/project
export FIVEBR_HOME=/path/to/project
fivebr project-status
fivebr doctor
fivebr build
fivebr validate
```

Mutable runtime data remains under `FIVEBR_HOME`. Installed application code stays separate from runtime configuration, production database rows, generated filters, releases, reports, audit logs, and runtime backups.

## Package safety

The candidate package must not contain:

- Production policies.
- Production database rows.
- Audit logs.
- Suggestion decisions.
- Runtime reports.
- Runtime backups.
- Local credentials or secrets.

The expected candidate Wheel name is:

```text
fivebr-2.2.0rc1-py3-none-any.whl
```

Its exact filename and SHA-256 digest must be recorded from CI before any publication decision.

## Remaining blockers

1. Independent technical review remains unavailable and pending.
2. PR #9 must remain Draft until the maintainer explicitly accepts the residual risk.
3. Hosted CI must pass on the final candidate commit after all version-document changes.
4. No final `2.2.0` metadata, tag, or release may be created from this document.

## Historical notes

The previous 1.9.0 final release notes are archived at `docs/RELEASE_NOTES_1.9.0.md`. Historical 2.0.0 notes remain at `docs/RELEASE_NOTES_2.0.0.md`.
