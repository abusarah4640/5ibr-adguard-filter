# Code review remediation

All deployment-blocking findings in the multilingual/auth review have been addressed.

| Finding | Resolution |
|---|---|
| Missing CSRF protection | Global synchronizer-token validation covers every POST request; tokens are injected into every rendered POST form. |
| Roles not enforced | Route decorators enforce admin/editor/viewer policy. Build, delete, manual readiness approval, and suggestion approval are admin-only. |
| Empty user database fails open | All mutations now fail closed and redirect unauthenticated users to login, regardless of user count. |
| Language-switch open redirect | Login and language switching share strict local-path validation; protocol-relative and backslash targets are rejected. |
| Insecure production cookies | Production mode enables Secure, HttpOnly, SameSite cookies with application-specific names; an explicit development override remains available. |
| Random production secret | `FIVEBR_ENV=production` refuses startup unless `FIVEBR_SECRET_KEY` is set. |
| Weak settings validation | Timezones use `zoneinfo.available_timezones()`, date formats are allowlisted, profile lengths are bounded, and usernames follow a strict 3-64 character pattern. |
| Shallow security tests | A complete POST-route CSRF matrix and negative tests for roles, empty databases, inactive users, redirects, validation, session lifetime, secrets, and cookies were added. |
| Bootstrap password lifecycle | Migration notes now document a root-owned systemd `EnvironmentFile` workflow and mandatory post-provision removal/restart verification. |

Verification: **596 tests passed**. This includes a dedicated regression test proving every fresh `create_app()` instance receives all analyzer UX helpers. The remaining warning is a Flask-Login 0.6.3 internal use of `datetime.utcnow()` and does not originate in project code.
