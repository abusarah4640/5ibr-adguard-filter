# Contributing to 5ibr

## Before submitting rules

- Verify the rule.
- Do not block login services.
- Do not block update servers.
- Prefer specific domains over wildcards.
- Avoid duplicates.

## Development

Before opening a Pull Request run:

```bash
python scripts/fix.py
python scripts/validate.py
python scripts/build.py
pytest
```

## Commit Messages

Examples:

- Add LG Smart TV rules
- Improve validator
- Fix duplicate rules
- Update telemetry filter