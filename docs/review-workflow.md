# Review Workflow

Phase 3 introduces a community-ready review path.

```text
New Domain
    ↓
Pending
    ↓
Review
    ↓
Approved / Rejected
    ↓
Build uses Approved only
```

## Submit a pending domain

```bash
python fivebr.py review submit \
  --domain example.com \
  --vendor Example \
  --category Telemetry \
  --filter telemetry \
  --confidence 80 \
  --source "Manual" \
  --evidence "https://example.com" \
  --notes "Observed telemetry endpoint"
```

## List pending domains

```bash
python fivebr.py review pending
```

## Approve

```bash
python fivebr.py review approve example.com --reviewer ibrahim
```

## Reject

```bash
python fivebr.py review reject example.com --reviewer ibrahim --notes "Insufficient evidence"
```

Only rows with `Status=Approved` are included in build output.
