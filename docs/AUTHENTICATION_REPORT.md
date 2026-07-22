# Authentication report

Authentication uses Flask-Login and Werkzeug's adaptive password hashing. Users and preferences are held in a separate SQLite database at `data/web_users.sqlite3`; the project domain database schema is not modified.

Features include persistent user identities, active-state support, enforced `admin`/`editor`/`viewer` roles, remember-me cookies, logout by POST, centralized open-redirect protection, configurable 30-minute session expiry, synchronizer-token CSRF protection on every POST route, password changes requiring the current password, and a twelve-character minimum for new passwords. Cookies are HttpOnly and SameSite=Lax; production mode enables Secure cookies by default.

No insecure default credentials are created. On the first production start, set `FIVEBR_ADMIN_PASSWORD` to a strong value (at least twelve characters); the initial `admin` account is created only when the user database is empty. Set `FIVEBR_ENV=production` and a stable, high-entropy `FIVEBR_SECRET_KEY`; startup fails if the production secret is absent. `FIVEBR_SESSION_TIMEOUT_MINUTES` controls inactivity lifetime.

All mutation routes fail closed even when the user database is empty. Editors may analyze and edit records; build, deletion, manual readiness approval, and suggestion approval are restricted to administrators. Viewers cannot mutate application state.
