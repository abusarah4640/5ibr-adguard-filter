# CLI Specification

Status: Stable for v1.0.0-beta

## Contract

`fivebr.py` is a command router. Business logic belongs in command modules or services.

```text
python fivebr.py <command> [options]
```

## Command Registry

All public commands must be registered in `COMMANDS` in `fivebr.py`. Each command module exposes:

```python
def main(argv):
    ...
```

## Stable Commands

- `build` — generate filters, config outputs and releases.
- `validate` — validate generated filter and release consistency.
- `stats` — show database statistics.
- `report` — generate reports.
- `search` — find domains.
- `add` — add an approved domain directly.
- `update` — update an existing domain.
- `remove` — remove a domain after confirmation.
- `list` — list database rows with filters.
- `doctor` — run project health checks.
- `normalize` — normalize database values.
- `export` — export database to CSV, JSON or Markdown.
- `import` — import database rows.
- `review` — submit, list, approve or reject pending domains.

## Interactive Input

Interactive commands must print prompts on their own lines. They must not combine labels and user input on the same terminal line when the workflow expects line-by-line prompts.

## Compatibility

Commands must preserve unknown CSV columns and avoid schema-destructive writes.
