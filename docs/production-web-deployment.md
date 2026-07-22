# Production Web Deployment and Rollback

The 5ibr administration application must run behind an authenticated TLS gateway. Gunicorn must listen on loopback only. Port 8089 must never be allowed from an untrusted network.

## Required topology

Browser -> TLS and access gateway -> host loopback -> Gunicorn

The current deployment uses Cloudflare Access with a host-network Cloudflared tunnel. Gunicorn listens on `127.0.0.1:8089`.

## Preflight

Run from the intended revision:

    cd /opt/5ibr
    git status --short --branch
    /opt/5ibr/.venv/bin/python -m pytest -q
    /opt/5ibr/.venv/bin/fivebr build
    /opt/5ibr/.venv/bin/fivebr validate

Do not deploy from a dirty worktree. Record `git rev-parse HEAD` and the active systemd unit. Never print the environment file or process environment.

## Protected environment

Create `/etc/fivebr-web.env` from `deploy/fivebr-web.env.example`, replace the secret placeholder and hostname, then protect it:

    sudo chown root:root /etc/fivebr-web.env
    sudo chmod 600 /etc/fivebr-web.env

Production requires `FIVEBR_ENV=production`, a stable `FIVEBR_SECRET_KEY`, a public hostname in `FIVEBR_TRUSTED_HOSTS`, and `FIVEBR_COOKIE_SECURE=true`. Changing the secret invalidates existing sessions.

## Install the service

Back up the active unit, install the template, verify it, and restart:

    timestamp=$(date -u +%Y%m%dT%H%M%SZ)
    sudo cp --preserve=mode,ownership,timestamps \
      /etc/systemd/system/fivebr-web.service \
      "/etc/systemd/system/fivebr-web.service.before-$timestamp"
    sudo install --owner=root --group=root --mode=644 \
      deploy/fivebr-web.service \
      /etc/systemd/system/fivebr-web.service
    sudo systemd-analyze verify /etc/systemd/system/fivebr-web.service
    sudo systemctl daemon-reload
    sudo systemctl restart fivebr-web

## Health checks

Wait for the socket, not only the initial systemd active state:

    for attempt in $(seq 1 30); do
      ss -ltnH | grep -q '127.0.0.1:8089' && break
      sleep 1
    done
    systemctl is-active fivebr-web
    ss -ltnp | grep ':8089'

Using the configured public hostname, expect a login redirect (`302`), a session cookie containing `Secure`, and `400` for an untrusted Host header. Verify the public access gateway separately.

## Firewall

After every health check succeeds, remove any public Gunicorn rule:

    sudo ufw status numbered
    sudo ufw --force delete allow 8089/tcp
    sudo ufw status

Verify Gunicorn still listens only on `127.0.0.1`.

## Rollback

Never restore a unit that binds Gunicorn to `0.0.0.0` or disables production security. If an application revision fails, retain the hardened unit and environment, restore the previously qualified revision, reinstall locked dependencies, restart, wait for the socket, and repeat every health check.

Restore a previous unit only when it is known to be secure:

    sudo cp --preserve=mode,ownership,timestamps \
      /etc/systemd/system/fivebr-web.service.before-TIMESTAMP \
      /etc/systemd/system/fivebr-web.service
    sudo systemctl daemon-reload
    sudo systemctl restart fivebr-web

## Recovery drill record

On 2026-07-22, production moved from `0.0.0.0:8089` to `127.0.0.1:8089`. The inline secret moved to a root-owned mode-600 environment file, trusted-host enforcement and Secure cookies were enabled, and public IPv4 and IPv6 firewall rules for 8089 were removed.

An initial check observed systemd active before the socket was ready and triggered rollback. The previous unit could not boot under the new fail-closed requirements. The hardened unit was reapplied, the check was corrected to poll the socket, and local and Cloudflare Access checks passed. Therefore rollback must never target a known-insecure unit and health checks must poll the socket.
