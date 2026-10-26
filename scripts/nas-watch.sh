#!/bin/bash
set -euo pipefail
if timeout --kill-after=1 12 runuser -u jdownloader --preserve-environment -- python3 /usr/local/lib/jdownloader/check-nas.py >/dev/null; then
  if [ -f /run/jdownloader-nas-blocked ]; then
    systemctl start jdownloader
    # Startup/engine updates may take minutes. Keep the marker until the API
    # accepts the prior running state; the next timer tick retries safely.
    if python3 /usr/local/lib/jdownloader/nas-controller.py recover; then
      rm -f /run/jdownloader-nas-blocked
      logger -t jdownloader-nas 'NAS wieder verfügbar; vorheriger Downloadbetrieb wiederhergestellt.'
    fi
  else
    python3 /usr/local/lib/jdownloader/nas-controller.py remember
  fi
else
  # Record the blocked state before stopping: a busy CIFS operation can make
  # systemctl stop exceed this watch service's timeout. Recovery must still
  # know that it needs to start the engine after the NAS becomes healthy.
  python3 /usr/local/lib/jdownloader/nas-controller.py block
  systemctl stop jdownloader
  logger -t jdownloader-nas 'NAS nicht verfügbar; JDownloader deaktiviert.'
fi
