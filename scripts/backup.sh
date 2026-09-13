#!/bin/bash
set -euo pipefail
test "$(id -u)" = 0
TARGET=${1:-/var/backups/jdownloader-web}
install -d -m 700 "$TARGET"
BACKUP=$(mktemp -d)
trap 'rm -rf -- "$BACKUP"' EXIT
restart_jd=false
systemctl is-active --quiet jdownloader && restart_jd=true
systemctl stop jdownloader-nas-watch.timer jdownloader
trap 'rm -rf -- "$BACKUP"; systemctl start jdownloader-nas-watch.timer; if $restart_jd; then systemctl start jdownloader; fi' EXIT
python3 - "$BACKUP/app.db" <<'PY'
import sqlite3,sys
source=sqlite3.connect('/var/lib/jdownloader-web/app.db')
target=sqlite3.connect(sys.argv[1])
source.backup(target)
target.close(); source.close()
PY
cp -a /etc/jdownloader-web "$BACKUP/web-config"
cp -a /var/lib/jdownloader/cfg "$BACKUP/jdownloader-cfg"
FILE="$TARGET/jdownloader-$(date +%Y%m%d-%H%M%S).tar.gz"
umask 077
tar -czf "$FILE" -C "$BACKUP" .
echo "Backup erstellt: $FILE"
