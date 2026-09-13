#!/bin/bash
set -euo pipefail
PROJECT=/opt/jdownloader-web
test "$(id -u)" = 0
bash "$PROJECT/scripts/backup.sh"
"$PROJECT/venv/bin/pip" install -q -r "$PROJECT/backend/requirements.txt"
cd "$PROJECT/frontend"
npm ci --no-fund --no-audit
npm run build
install -m 755 "$PROJECT/scripts/check-nas.py" /usr/local/lib/jdownloader/check-nas.py
install -m 755 "$PROJECT/scripts/nas-watch.sh" /usr/local/sbin/jdownloader-nas-watch
install -m 755 "$PROJECT/scripts/backup.sh" /usr/local/sbin/backup-jdownloader-web
install -m 644 "$PROJECT/nginx/jdownloader-web.conf" /etc/nginx/sites-available/jdownloader-web
install -m 644 "$PROJECT"/systemd/*.service "$PROJECT"/systemd/*.timer /etc/systemd/system/
nginx -t
systemctl daemon-reload
systemctl restart jdownloader jdownloader-web jdownloader-nas-watch.timer
systemctl reload nginx
bash "$PROJECT/scripts/healthcheck.sh"
