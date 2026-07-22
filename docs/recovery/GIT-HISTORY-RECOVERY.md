# Git History Recovery Report

## Status

Repository history partially recovered and attached.

## Incident

The active project filesystem at `/opt/5ibr` was found without its local
`.git` directory.

The local Git metadata covering the later development period was unavailable.

## Recovered Upstream History

An existing upstream repository was identified:

`https://github.com/abusarah4640/5ibr-adguard-filter`

The upstream `main` branch contained 73 historical commits at recovery time.

Recovered upstream tip:

`d28ef99ba7853e87916e4e4ed95c64c0c95a0cd3`

This history represents an earlier generation of the project around Phase 4
and the v1.0.0-beta stabilization target.

The current filesystem contains substantial later development beyond that
upstream state.

## Unverified Recorded Commit Identifiers

The following previously recorded identifiers were not found in the recovered
upstream history and remain independently unverified:

- Qualified baseline: `a4e892941b99b7417e2722f966cdf95edcceec3f`
- Release infrastructure: `f8e10448964bb0ccc5a5bdc2f50d77d0a684c8db`

These identifiers must not be used as executable release references.

## Recovery Decision

The recovered upstream history is retained as the historical foundation.

The verified current filesystem state will be committed on top of upstream
commit `d28ef99ba7853e87916e4e4ed95c64c0c95a0cd3` as a Recovery Continuation
Baseline.

No missing intermediate commits will be fabricated or represented as
recovered.

## Recovery Inventory

At the time of pre-commit inspection:

- Existing tracked files modified: 81
- New files recovered from the current filesystem: 936
- Existing tracked files deleted: 0

Runtime databases, query logs, backups, local virtual environments, generated
package metadata, emergency copies, and local credentials are excluded from
version control.

A pre-attachment filesystem archive was created at:

`5ibr-pre-history-attach-20260721-091701.tar.gz` (stored externally)

The archive is an external operational recovery artifact and is not stored in
this repository.

## Release Impact

RC1 remains NOT READY.

All qualification evidence recorded against unavailable commit identifiers
must be treated as historical evidence only.

Qualification must be repeated against the Recovery Continuation Baseline:

1. Local qualification
2. Hosted CI
3. Independent technical review
4. Deployment and rollback drills
5. Release gate review
6. Release maintainer approval

No tag or release publication is authorized by this recovery action.
EOFcd /opt/5ibr

cat > reports/release/v2.4.0/RECOVERY/GIT-HISTORY-RECOVERY.md <<'EOF'
# Git History Recovery Report

## Status

Repository history partially recovered and attached.

## Incident

The active project filesystem at `/opt/5ibr` was found without its local
`.git` directory.

The local Git metadata covering the later development period was unavailable.

## Recovered Upstream History

An existing upstream repository was identified:

`https://github.com/abusarah4640/5ibr-adguard-filter`

The upstream `main` branch contained 73 historical commits at recovery time.

Recovered upstream tip:

`d28ef99ba7853e87916e4e4ed95c64c0c95a0cd3`

This history represents an earlier generation of the project around Phase 4
and the v1.0.0-beta stabilization target.

The current filesystem contains substantial later development beyond that
upstream state.

## Unverified Recorded Commit Identifiers

The following previously recorded identifiers were not found in the recovered
upstream history and remain independently unverified:

- Qualified baseline: `a4e892941b99b7417e2722f966cdf95edcceec3f`
- Release infrastructure: `f8e10448964bb0ccc5a5bdc2f50d77d0a684c8db`

These identifiers must not be used as executable release references.

## Recovery Decision

The recovered upstream history is retained as the historical foundation.

The verified current filesystem state will be committed on top of upstream
commit `d28ef99ba7853e87916e4e4ed95c64c0c95a0cd3` as a Recovery Continuation
Baseline.

No missing intermediate commits will be fabricated or represented as
recovered.

## Recovery Inventory

At the time of pre-commit inspection:

- Existing tracked files modified: 81
- New files recovered from the current filesystem: 936
- Existing tracked files deleted: 0

Runtime databases, query logs, backups, local virtual environments, generated
package metadata, emergency copies, and local credentials are excluded from
version control.

A pre-attachment filesystem archive was created at:

`5ibr-pre-history-attach-20260721-091701.tar.gz` (stored externally)

The archive is an external operational recovery artifact and is not stored in
this repository.

## Release Impact

RC1 remains NOT READY.

All qualification evidence recorded against unavailable commit identifiers
must be treated as historical evidence only.

Qualification must be repeated against the Recovery Continuation Baseline:

1. Local qualification
2. Hosted CI
3. Independent technical review
4. Deployment and rollback drills
5. Release gate review
6. Release maintainer approval

No tag or release publication is authorized by this recovery action.
