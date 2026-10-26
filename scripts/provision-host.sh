#!/bin/bash
# Compatibility entry point for existing local project sources.
set -euo pipefail
PROJECT=$(cd -- "$(dirname -- "$0")/.." && pwd)
exec python3 "$PROJECT/scripts/proxmox-install.py" "$@"
