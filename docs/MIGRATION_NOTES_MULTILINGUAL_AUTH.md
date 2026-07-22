# Multilingual and authentication migration notes

1. Install the updated package so `Flask-Login>=0.6.3` is present.
2. Back up the runtime directory.
3. Set `FIVEBR_ENV=production` and `FIVEBR_SECRET_KEY` to a stable random secret. Production startup refuses a missing secret and enables Secure cookies.
4. Set `FIVEBR_ADMIN_PASSWORD` for the first launch, then remove it from the process environment after the administrator row exists.
5. Optionally set `FIVEBR_SESSION_TIMEOUT_MINUTES` (default: 30).
6. Start the web application and sign in as `admin`; change the bootstrap password in Settings.
7. Remove `FIVEBR_ADMIN_PASSWORD` from the service environment and restart. With systemd, keep secrets in a root-owned `EnvironmentFile`, delete the bootstrap-password line after provisioning, run `systemctl daemon-reload`, and restart the service. Verify the variable is absent with the service manager's environment inspection command.

The new `data/web_users.sqlite3` file is created automatically. If no administrator is provisioned, mutations remain locked rather than becoming anonymous. No migration touches the domain database, analyzer, knowledge engine, filters, suggestions, or API-shaped values. Existing language cookies continue to work. Authenticated preferences supersede browser detection through the session after login.

Rollback is code-only: stop the application and deploy the prior release. Retain `web_users.sqlite3` for a later retry; older releases ignore it.
