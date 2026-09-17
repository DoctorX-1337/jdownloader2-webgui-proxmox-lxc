#!/bin/bash
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
: "${AMO_JWT_ISSUER:?AMO_JWT_ISSUER fehlt}"
: "${AMO_JWT_SECRET:?AMO_JWT_SECRET fehlt}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
python3 "$PROJECT/scripts/build-browser-extension.py"
mkdir -p "$WORK/source" "$PROJECT/browser-extension/signed"
python3 - "$PROJECT/frontend/public/jdownloader2-firefox-extension.zip" "$WORK/source" <<'PY'
import sys,zipfile
with zipfile.ZipFile(sys.argv[1]) as archive:archive.extractall(sys.argv[2])
PY
npx --yes web-ext sign --source-dir "$WORK/source" --artifacts-dir "$WORK/signed" --channel unlisted --api-key "$AMO_JWT_ISSUER" --api-secret "$AMO_JWT_SECRET"
signed="$(find "$WORK/signed" -maxdepth 1 -type f -name '*.xpi' -print -quit)"
test -n "$signed"
install -m 644 "$signed" "$PROJECT/browser-extension/signed/jdownloader2-firefox-extension.xpi"
python3 "$PROJECT/scripts/build-browser-extension.py"
echo 'Signierte Firefox-XPI erstellt. Zugangsdaten wurden nicht gespeichert.'
