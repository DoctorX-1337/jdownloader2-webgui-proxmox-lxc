#!/bin/bash
set -euo pipefail
if timeout --kill-after=1 12 runuser -u jdownloader --preserve-environment -- python3 /usr/local/lib/jdownloader/check-nas.py >/dev/null; then
  if [ -f /run/jdownloader-nas-blocked ]; then
    systemctl start jdownloader
    rm -f /run/jdownloader-nas-blocked
    logger -t jdownloader-nas 'NAS wieder verfügbar; JDownloader gestartet.'
  fi
else
  systemctl stop jdownloader
  touch /run/jdownloader-nas-blocked
  logger -t jdownloader-nas 'NAS nicht verfügbar; JDownloader deaktiviert.'
fi
