# Localization report

## Scope and architecture

The web presentation layer was audited across `web/app.py`, all active Jinja templates, helpers, and values supplied by services. Stored database values, analyzer values, enums, API-shaped data, and business rules remain unchanged. Translation happens only at the display boundary.

The catalog contains 309 canonical keys in both English and Arabic. Automated tests enforce identical locale key sets and verify that every literal `t()` key used by a template exists in every locale. Dynamic display helpers cover statuses, categories, vendors, recommendations, guardrails, confidence levels, and decisions while preserving their raw internal values.

## Language manager

Language resolution is, in order: `?lang=`, `fivebr_lang` cookie, session preference, browser `Accept-Language`, and English. The navbar selector updates immediately, persists to both session and a one-year SameSite cookie, and updates an authenticated user's preference. The document `lang` and `dir` attributes switch automatically; Arabic renders RTL and English LTR.

## Coverage

| Locale | Keys | Key coverage | Direction |
|---|---:|---:|---|
| English (`en`) | 309 | 100% | LTR |
| Arabic (`ar`) | 309 | 100% | RTL |

Dashboard, intelligence, analysis, domains, suggestions, releases, review queue, audit, action output, authentication, and settings templates are included in the catalog audit.

## Adding a language

Add its code to `SUPPORTED_LANGS`, add a catalog with the same canonical key set, add its direction rule if RTL, and add it to the navbar/settings selectors. The catalog-alignment tests will report any missing keys.
