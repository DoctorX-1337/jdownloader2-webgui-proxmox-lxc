#!/bin/bash
set -euo pipefail
if timeout --kill-after=1 12 runuser -u jdownloader --preserve-environment -- python3 /usr/local/lib/jdownloader/check-nas.py >/dev/null; then
  if [ -f /run/jdownloader-nas-blocked ]; then
    systemctl start jdownloader
    rm -f /run/jdownloader-nas-blocked
    logger -t jdownloader-nas 'NAS wieder verfügbar; JDownloader gestartet.'
  fi
else
  # Record the blocked state before stopping: a busy CIFS operation can make
  # systemctl stop exceed this watch service's timeout. Recovery must still
  # know that it needs to start the engine after the NAS becomes healthy.
  touch /run/jdownloader-nas-blocked
  systemctl stop jdownloader
  logger -t jdownloader-nas 'NAS nicht verfügbar; JDownloader deaktiviert.'
fi
