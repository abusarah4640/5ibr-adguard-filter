# 5ibr Web Admin UI

The Web UI is an authenticated Flask administration interface on top of the
existing toolkit. It does not replace the CLI.

## Local development

Install the project and start the development server:

```bash
cd /opt/5ibr
source .venv/bin/activate
python -m pip install --editable .
fivebr-web
```

The development entry point listens on loopback only:

```text
http://127.0.0.1:8089
```

`fivebr-web` is not a production server and refuses to start when
`FIVEBR_ENV=production`.

## Production

Run the WSGI application with a production server such as Gunicorn. Configure
the service through a protected environment file containing at least:

```text
FIVEBR_ENV=production
FIVEBR_SECRET_KEY=<random-secret>
FIVEBR_TRUSTED_HOSTS=filters.example.com
FIVEBR_COOKIE_SECURE=true
```

Example Gunicorn command:

```bash
gunicorn \
  --workers 2 \
  --bind 127.0.0.1:8089 \
  web.app:app
```

Place Gunicorn behind a TLS reverse proxy or authenticated tunnel. Do not expose
the Flask development server or Gunicorn directly to an untrusted network.

For the tested systemd deployment, health checks, firewall requirements, and
rollback procedure, see `docs/production-web-deployment.md`.

## Features

- Authenticated dashboard and operational diagnostics.
- Role-controlled domain and review workflows.
- Query-log uploads confined to the runtime upload directory.
- Release, suggestion, readiness, and audit views.
- Doctor, validate, build, and analysis actions subject to authorization and
  CSRF protection.
