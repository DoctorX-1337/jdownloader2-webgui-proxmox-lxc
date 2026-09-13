#!/bin/bash
set -euo pipefail
for attempt in $(seq 1 45); do
  if STATUS=$(curl -fsS --max-time 3 http://127.0.0.1/api/health 2>/dev/null) &&
    printf '%s' "$STATUS" | python3 -c 'import json,sys; h=json.load(sys.stdin); assert h.get("application")==h.get("jdownloader")==h.get("nas")=="online" and h.get("nasWritable")' 2>/dev/null; then
    printf '%s\n' "$STATUS" | python3 -m json.tool
    exit 0
  fi
  sleep 2
done
echo 'Dienste nach 90 Sekunden nicht vollständig verfügbar.' >&2
exit 1
