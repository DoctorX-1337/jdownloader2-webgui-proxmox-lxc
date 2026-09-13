#!/bin/bash
set -euo pipefail
test "$(id -u)" = 0
test -f /tmp/jd2-nas-public.pub
test -f /tmp/jd2-nas-key
test -f /tmp/jd2-nas-known-hosts
useradd --system --create-home --home-dir /var/lib/jd2mount --shell /bin/sh jd2mount 2>/dev/null || id jd2mount
install -d -m 750 -o root -g jd2mount /var/lib/jd2mount /var/lib/jd2mount/.ssh
{ printf 'from="192.0.2.20",command="sudo -n /usr/local/sbin/jd2-nas-rpc",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty '; cat /tmp/jd2-nas-public.pub; } > /var/lib/jd2mount/.ssh/authorized_keys
chown root:jd2mount /var/lib/jd2mount/.ssh/authorized_keys
chmod 640 /var/lib/jd2mount/.ssh/authorized_keys
install -d /usr/local/lib/jdownloader-nas
install -m 755 /tmp/nas_host.py /usr/local/lib/jdownloader-nas/nas_host.py
printf '#!/bin/sh\nexec /usr/bin/python3 /usr/local/lib/jdownloader-nas/nas_host.py\n' > /usr/local/sbin/jd2-nas-rpc
chmod 755 /usr/local/sbin/jd2-nas-rpc
if ! command -v sudo >/dev/null; then apt-get update -qq; DEBIAN_FRONTEND=noninteractive apt-get install -y -qq sudo; fi
printf 'jd2mount ALL=(root) NOPASSWD: /usr/local/sbin/jd2-nas-rpc ""\n' > /etc/sudoers.d/jd2mount
chmod 440 /etc/sudoers.d/jd2mount
visudo -cf /etc/sudoers.d/jd2mount
python3 - <<'PY'
from pathlib import Path
import json
p=Path('/etc/jdownloader-nas/state.json')
if not p.exists():
 p.write_text(json.dumps({'target':r'\\NAS-SERVER\media\Downloads','status':'ready','message':'NAS verbunden.'})); p.chmod(0o600)
PY
pct push 200 /tmp/jd2-nas-key /etc/jdownloader-web/nas_key
pct push 200 /tmp/jd2-nas-known-hosts /etc/jdownloader-web/nas_known_hosts
pct exec 200 -- chown jdweb:jdownloader /etc/jdownloader-web/nas_key /etc/jdownloader-web/nas_known_hosts
pct exec 200 -- chmod 600 /etc/jdownloader-web/nas_key
pct exec 200 -- chmod 644 /etc/jdownloader-web/nas_known_hosts
rm -f /tmp/jd2-nas-key /tmp/jd2-nas-public.pub /tmp/jd2-nas-known-hosts
echo 'Eingeschränkte NAS-Verwaltung eingerichtet.'
