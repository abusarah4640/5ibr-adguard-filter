# 5ibr Filter Toolkit v1.5.0 Upgrade Guide

## 1. Backup

```bash
sudo cp -a /opt/5ibr /opt/5ibr-backups/5ibr-$(date +%F-%H%M)
sudo ls -lh /opt/5ibr-backups
```

## 2. Upload from Windows

```powershell
scp -P 2222 "C:\Users\saja1\Downloads\5ibr-adguard-filter-v1.5.0-admin-platform.zip" ibrahim@<SERVER_LAN_IP>:~
```

## 3. Move ZIP to /opt

```bash
sudo mv ~/5ibr-adguard-filter-v1.5.0-admin-platform.zip /opt/
```

## 4. Extract update

```bash
cd /opt
sudo mkdir -p 5ibr-update-v1.5.0
sudo unzip 5ibr-adguard-filter-v1.5.0-admin-platform.zip -d 5ibr-update-v1.5.0
sudo chown -R ibrahim:ibrahim /opt/5ibr-update-v1.5.0
```

## 5. Safe merge

This preserves your local database, analyzer config, reports, data, and releases.

```bash
sudo rsync -av \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude 'database/domains.csv' \
  --exclude 'config/analyzer.json' \
  --exclude 'reports/' \
  --exclude 'data/' \
  --exclude 'releases/' \
  /opt/5ibr-update-v1.5.0/ /opt/5ibr/
```

## 6. Install and restart

```bash
sudo chown -R ibrahim:ibrahim /opt/5ibr
cd /opt/5ibr
source .venv/bin/activate
pip install -e .
sudo systemctl restart fivebr-web
sudo systemctl status fivebr-web --no-pager
```

## 7. Verify CLI

```bash
fivebr doctor
fivebr validate
fivebr build
pytest -q
```

## 8. Verify Web UI

Open:

```text
https://filters.5ibr.com
```

Test:
- Dashboard
- Domains
- Add Domain
- Edit Domain
- Suggestions
- Releases
- Audit
- Arabic/English switch

## 9. Template validation

```bash
cd /opt/5ibr
source .venv/bin/activate
python - <<'PY'
from web.app import app
with app.app_context():
    for name in app.jinja_loader.list_templates():
        app.jinja_env.get_template(name)
        print("OK", name)
PY
```

## 10. Rollback

```bash
sudo systemctl stop fivebr-web
sudo rm -rf /opt/5ibr
sudo cp -a /opt/5ibr-backups/<backup-name> /opt/5ibr
sudo chown -R ibrahim:ibrahim /opt/5ibr
sudo systemctl start fivebr-web
```
