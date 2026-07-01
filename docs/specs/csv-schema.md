# CSV Schema Specification

Status: Stable for v1.0.0-beta

The canonical database is:

```text
database/domains.csv
```

## Required Columns

| Column | Meaning | Required |
| --- | --- | --- |
| `Domain` | Domain or rule target | Yes |
| `Vendor` | Owner, service, platform or product | Yes |
| `Category` | Human classification | Yes |
| `Filter` | Output filter bucket | Yes |
| `Confidence` | Reviewer confidence from 0 to 100 | Yes |
| `Status` | Review/build status | Yes |

## Standard Metadata Columns

| Column | Meaning |
| --- | --- |
| `Created` | Creation date/time when available |
| `Updated` | Last update date/time when available |
| `Reviewer` | Reviewer name or handle |
| `Source` | Source of the entry |
| `Evidence` | Evidence URL, note or reference |
| `Notes` | Free-form internal notes |

## Status Values

Allowed status values are:

```text
Pending
Approved
Rejected
Disabled
```

Only `Approved` rows should be included in normal release builds.

## Integrity Rules

- `Domain` must not be empty.
- `Vendor` must not be empty.
- `Category` must be known to project config.
- `Filter` must map to a known filter output.
- `Confidence` must be an integer from 0 to 100.
- Unknown columns must be preserved.
