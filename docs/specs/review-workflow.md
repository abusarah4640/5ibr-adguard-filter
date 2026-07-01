# Review Workflow Specification

Status: Stable for v1.0.0-beta

## Workflow

```text
New Domain
    ↓
Pending
    ↓
Review
    ↓
Approved / Rejected
    ↓
Build
```

## Commands

```bash
python fivebr.py review submit --domain example.com --vendor Example --category Telemetry --filter telemetry --confidence 80
python fivebr.py review pending
python fivebr.py review approve example.com --reviewer ibrahim
python fivebr.py review reject example.com --reviewer ibrahim --notes "Insufficient evidence"
```

## Rules

- New community entries should default to `Pending`.
- Approval requires valid integrity checks.
- Rejection should keep a note when evidence is insufficient or the rule is unsafe.
- Build output should prefer `Approved` rows.

## Reviewer Responsibilities

Reviewers check domain accuracy, vendor classification, category, filter target, confidence score, source and evidence.
