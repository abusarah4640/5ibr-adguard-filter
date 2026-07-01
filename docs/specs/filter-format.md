# Filter Format Specification

Status: Stable for v1.0.0-beta

Generated filter files target AdGuard Home compatible DNS blocklists.

## Source of Truth

Rules are generated from `database/domains.csv`. Manual edits to generated output files should not be treated as source changes.

## Output Locations

```text
filters/*.txt
releases/*.txt
```

## Rule Style

Domain blocking rules should be written in AdGuard-compatible form. Generated files should be deterministic so diffs remain readable.

## Whitelist

Whitelist entries belong in:

```text
filters/whitelist.txt
```

Whitelist behavior must be documented when a release bundle includes it.

## Release Bundles

Release bundles combine category filters for practical use cases such as home, privacy, gaming, family, strict-family and all.
