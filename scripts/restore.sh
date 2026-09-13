#!/bin/bash
set -euo pipefail
test "$(id -u)" = 0
ARCHIVE=${1:?Backup-Datei angeben}
BACKUP=$(mktemp -d)
trap 'rm -rf -- "$BACKUP"' EXIT
# Reject absolute paths, traversal, links and special files before extraction.
python3 - "$ARCHIVE" "$BACKUP" <<'PY'
import sys,tarfile
from pathlib import PurePosixPath
with tarfile.open(sys.argv[1]) as t:
 for member in t.getmembers():
  p=PurePosixPath(member.name)
  if p.is_absolute() or '..' in p.parts or not (member.isfile() or member.isdir()): raise SystemExit('Ungültiges Backup-Archiv')
 t.extractall(sys.argv[2],filter='data')
PY
test -f "$BACKUP/app.db" && test -d "$BACKUP/web-config" && test -d "$BACKUP/jdownloader-cfg"
bash /opt/jdownloader-web/scripts/backup.sh
systemctl stop jdownloader-web jdownloader-nas-watch.timer jdownloader
cp -a "$BACKUP/web-config/." /etc/jdownloader-web/
rm -f /var/lib/jdownloader-web/app.db-wal /var/lib/jdownloader-web/app.db-shm
cp "$BACKUP/app.db" /var/lib/jdownloader-web/app.db
cp -a "$BACKUP/jdownloader-cfg/." /var/lib/jdownloader/cfg/
chown -R jdweb:jdownloader /var/lib/jdownloader-web
chown -R jdownloader:jdownloader /var/lib/jdownloader/cfg
chmod 640 /var/lib/jdownloader-web/app.db
chown root:jdownloader /etc/jdownloader-web /etc/jdownloader-web/config.env
chmod 750 /etc/jdownloader-web
chmod 640 /etc/jdownloader-web/config.env
for file in nas_key nas_known_hosts; do
  if [ -f "/etc/jdownloader-web/$file" ]; then
    chown jdweb:jdownloader "/etc/jdownloader-web/$file"
    chmod 600 "/etc/jdownloader-web/$file"
  fi
done
# Backups should not revive old browser sessions.
python3 - <<'PY'
import sqlite3
c=sqlite3.connect('/var/lib/jdownloader-web/app.db'); c.execute('DELETE FROM sessions'); c.commit(); c.close()
PY
systemctl start jdownloader jdownloader-web jdownloader-nas-watch.timer
bash /opt/jdownloader-web/scripts/healthcheck.sh
