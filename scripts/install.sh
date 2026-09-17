#!/bin/bash
set -euo pipefail
test "$(id -u)" = 0 || { echo 'Installation benötigt root im Container.'; exit 1; }
. /etc/os-release
test "$ID" = ubuntu || { echo 'Unterstützt: Ubuntu 24.04/26.04 LTS.'; exit 1; }
case "$VERSION_ID" in 24.04|26.04) ;; *) echo 'Nicht unterstützte Ubuntu-Version'; exit 1 ;; esac
PROJECT=$(cd -- "$(dirname -- "$0")/.." && pwd)
test "$PROJECT" = /opt/jdownloader-web || { echo 'Projekt zuerst nach /opt/jdownloader-web kopieren.'; exit 1; }
export DEBIAN_FRONTEND=noninteractive
printf 'Acquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/99force-ipv4
apt-get update -qq
apt-get upgrade -y -qq >/var/log/jdownloader-install-packages.log 2>&1
apt-get install -y -qq openjdk-21-jre python3-venv nginx curl ca-certificates nodejs npm nftables openssh-client unattended-upgrades >>/var/log/jdownloader-install-packages.log 2>&1
getent group jdownloader >/dev/null || groupadd --gid 1000 jdownloader
id jdownloader >/dev/null 2>&1 || useradd --system --uid 1000 --gid jdownloader --home-dir /var/lib/jdownloader --shell /usr/sbin/nologin jdownloader
id jdweb >/dev/null 2>&1 || useradd --system --uid 1001 --gid jdownloader --home-dir /var/lib/jdownloader-web --shell /usr/sbin/nologin jdweb
install -d -m 750 -o jdweb -g jdownloader /var/lib/jdownloader-web
install -d -m 750 -o root -g jdownloader /etc/jdownloader-web
if [ ! -f /etc/jdownloader-web/config.env ]; then install -m 640 -o root -g jdownloader "$PROJECT/config/config.env.example" /etc/jdownloader-web/config.env; fi
if [ ! -f /etc/jdownloader-web/browser-extension.token ]; then
  (umask 077; python3 -c 'import secrets; print(secrets.token_urlsafe(36))' > /etc/jdownloader-web/browser-extension.token)
fi
chown jdweb:jdownloader /etc/jdownloader-web/browser-extension.token
chmod 600 /etc/jdownloader-web/browser-extension.token
install -d /usr/local/lib/jdownloader
install -m 755 "$PROJECT/scripts/check-nas.py" /usr/local/lib/jdownloader/check-nas.py
timeout 12 runuser -u jdownloader -- python3 /usr/local/lib/jdownloader/check-nas.py
if [ ! -f /opt/jdownloader/JDownloader.jar ]; then
  cp "$PROJECT/scripts/check-nas.py" /tmp/check-nas.py
  cp "$PROJECT/systemd/jdownloader.service" /tmp/jdownloader.service
  bash "$PROJECT/scripts/bootstrap-jd.sh"
fi
python3 -m venv "$PROJECT/venv"
"$PROJECT/venv/bin/pip" install -q -r "$PROJECT/backend/requirements.txt"
if [ "${1:-}" = --admin-hash-file ]; then
  (cd "$PROJECT/backend"; runuser -u jdweb -- "$PROJECT/venv/bin/python" seed_admin.py "$2")
  rm -f -- "$2"
elif ! (cd "$PROJECT/backend"; "$PROJECT/venv/bin/python" -c 'from app.database import db,initialize; initialize(); c=db(); d=c.__enter__(); assert d.execute("SELECT COUNT(*) FROM users").fetchone()[0]>0'); then
  echo 'Ein Administrator-Hash muss mit --admin-hash-file angegeben werden. Siehe README.'
  exit 1
fi
python3 "$PROJECT/scripts/build-browser-extension.py"
cd "$PROJECT/frontend"
if [ -f package-lock.json ]; then npm ci --no-fund --no-audit; else npm install --no-fund --no-audit; fi
npm run build
chmod -R a+rX "$PROJECT/frontend/dist"
install -m 644 "$PROJECT/nginx/jdownloader-web.conf" /etc/nginx/sites-available/jdownloader-web
ln -sfn /etc/nginx/sites-available/jdownloader-web /etc/nginx/sites-enabled/jdownloader-web
rm -f /etc/nginx/sites-enabled/default
nginx -t
install -m 644 "$PROJECT"/systemd/*.service "$PROJECT"/systemd/*.timer /etc/systemd/system/
install -m 755 "$PROJECT/scripts/nas-watch.sh" /usr/local/sbin/jdownloader-nas-watch
install -m 755 "$PROJECT/scripts/backup.sh" /usr/local/sbin/backup-jdownloader-web
install -m 644 "$PROJECT/config/nftables.conf" /etc/nftables.conf
nft -c -f /etc/nftables.conf
systemctl daemon-reload
systemctl enable nginx jdownloader jdownloader-web jdownloader-nas-watch.timer nftables unattended-upgrades
systemctl restart jdownloader jdownloader-web nginx nftables
systemctl start jdownloader-nas-watch.timer
systemctl disable --now ssh.socket ssh.service postfix 2>/dev/null || true
echo 'Installation abgeschlossen; Statusprüfung läuft.'
for attempt in $(seq 1 30); do
  if curl -fsS http://127.0.0.1/api/health | python3 -c 'import json,sys; h=json.load(sys.stdin); assert h["application"]==h["jdownloader"]==h["nas"]=="online" and h["nasWritable"]'; then echo 'Alle Dienste sind online.'; exit 0; fi
  sleep 2
done
echo 'Healthcheck noch nicht vollständig grün. Siehe journalctl.'
exit 1
