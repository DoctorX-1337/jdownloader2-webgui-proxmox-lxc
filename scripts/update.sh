#!/bin/bash
set -euo pipefail
PROJECT=/opt/jdownloader-web
test "$(id -u)" = 0
bash "$PROJECT/scripts/backup.sh"
"$PROJECT/venv/bin/pip" install -q -r "$PROJECT/backend/requirements.txt"
if [ ! -f /etc/jdownloader-web/browser-extension.token ]; then
  (umask 077; python3 -c 'import secrets; print(secrets.token_urlsafe(36))' > /etc/jdownloader-web/browser-extension.token)
fi
chown jdweb:jdownloader /etc/jdownloader-web/browser-extension.token
chmod 600 /etc/jdownloader-web/browser-extension.token
python3 "$PROJECT/scripts/build-browser-extension.py"
cd "$PROJECT/frontend"
npm ci --no-fund --no-audit
npm run build
chmod -R a+rX "$PROJECT/frontend/dist"
install -m 755 "$PROJECT/scripts/check-nas.py" /usr/local/lib/jdownloader/check-nas.py
install -m 755 "$PROJECT/scripts/nas-watch.sh" /usr/local/sbin/jdownloader-nas-watch
install -m 755 "$PROJECT/scripts/backup.sh" /usr/local/sbin/backup-jdownloader-web
install -m 644 "$PROJECT/nginx/jdownloader-web.conf" /etc/nginx/sites-available/jdownloader-web
install -m 644 "$PROJECT"/systemd/*.service "$PROJECT"/systemd/*.timer /etc/systemd/system/
nginx -t
systemctl daemon-reload
systemctl stop jdownloader
python3 - <<'PY'
import json
from pathlib import Path
path=Path('/var/lib/jdownloader/cfg/org.jdownloader.api.RemoteAPIConfig.json')
values=json.loads(path.read_text(encoding='utf-8'))
values['externinterfaceenabled']=True
values['externinterfacelocalhostonly']=True
path.write_text(json.dumps(values,separators=(',',':')),encoding='utf-8')
PY
chown jdownloader:jdownloader /var/lib/jdownloader/cfg/org.jdownloader.api.RemoteAPIConfig.json
systemctl restart jdownloader jdownloader-web jdownloader-nas-watch.timer
systemctl reload nginx
for attempt in $(seq 1 30); do
  listeners="$(ss -H -lnt '( sport = :9666 )' | awk '{print $4}')"
  [ -n "$listeners" ] && break
  sleep 1
done
[ -n "${listeners:-}" ] || { echo 'Click’n’Load-Listener wurde nicht gestartet.'; exit 1; }
while IFS= read -r address; do
  case "$address" in
    127.0.0.1:9666|'[::1]:9666') ;;
    *) systemctl stop jdownloader; echo 'Unsichere Click’n’Load-Bindung erkannt; JDownloader wurde gestoppt.'; exit 1 ;;
  esac
done <<< "$listeners"
bash "$PROJECT/scripts/healthcheck.sh"
