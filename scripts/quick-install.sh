#!/bin/bash
# Run from an interactive root console on the target Proxmox VE node.
set -euo pipefail
if [[ ${1:-} = --help ]]; then
  echo 'Proxmox VE: bash quick-install.sh [--check]'
  echo 'Downloads project sources and starts the interactive LXC installer.'
  exit 0
fi
[[ $(id -u) = 0 ]] || { echo 'Bitte als root auf dem Proxmox-VE-Knoten starten.'; exit 1; }
command -v pct >/dev/null || { echo 'Proxmox VE wurde nicht gefunden.'; exit 1; }
command -v python3 >/dev/null
command -v curl >/dev/null
[[ -t 0 && -t 1 ]] || { echo 'Bitte aus einer interaktiven Konsole mit bash starten, nicht an curl | bash übergeben.'; exit 1; }
stage=$(mktemp -d /var/tmp/jd2-install.XXXXXXXX)
trap 'rm -rf -- "$stage"' EXIT
chmod 700 "$stage"
# Optional immutable Git commit, otherwise the current main branch.
ref=${JD2_REF:-main}
[[ $ref = main || $ref =~ ^[0-9a-f]{40}$ ]] || { echo 'JD2_REF muss main oder eine vollständige Commit-ID sein.'; exit 1; }
curl --proto '=https' --tlsv1.2 -fsSL --retry 3 \
  "https://codeload.github.com/DoctorX-1337/jdownloader2-webgui-proxmox-lxc/tar.gz/$ref" -o "$stage/source.tar.gz"
tar -xzf "$stage/source.tar.gz" -C "$stage" --strip-components=1
python3 "$stage/scripts/proxmox-install.py" "$@"
