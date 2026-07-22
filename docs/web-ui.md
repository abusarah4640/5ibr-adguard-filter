# 5ibr Web Admin UI

The Web UI is a lightweight Flask admin interface on top of the existing toolkit.
It does not replace the CLI. It provides browser access to common workflows.

## Start

```bash
cd /opt/5ibr
source .venv/bin/activate
pip install -e .
fivebr-web
```

Open:

```text
http://SERVER-IP:8089
```

Example:

```text
http://<SERVER_LAN_IP>:8089
```

## Features

- Dashboard.
- List and search domains.
- Add domains.
- Edit domains.
- Delete domains.
- Run doctor, validate and build.
- Analyze a single domain.
- Analyze an AdGuard Home query log.
- View and download release files.

## Notes

This initial Web UI is intended for trusted local/admin use. For public exposure,
place it behind Nginx Proxy Manager and add authentication.
