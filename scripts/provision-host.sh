#!/bin/bash
set -euo pipefail
CT_ID=${CT_ID:-200}
if pct config "$CT_ID" >/dev/null 2>&1; then echo 'Container-ID bereits belegt; Abbruch.'; exit 1; fi
if ping -c 1 -W 2 192.0.2.20 >/dev/null; then echo 'Ziel-IP antwortet bereits; Abbruch.'; exit 1; fi
install -d -m 700 /etc/jdownloader-nas
python3 - <<'PY'
import subprocess, re, pathlib, os
fstab = subprocess.check_output(['pct','exec','201','--','cat','/etc/fstab'], text=True)
line = next(x for x in fstab.splitlines() if x.startswith('//192.0.2.30/media'))
credential = re.search(r'credentials=([^,\s]+)',line).group(1)
data = subprocess.check_output(['pct','exec','201','--','cat',credential])
path = pathlib.Path('/etc/jdownloader-nas/credentials')
path.write_bytes(data)
os.chmod(path,0o600)
PY
mountpoint -q /mnt/nas-server-jdownloader || install -d -m 000 /mnt/nas-server-jdownloader
MOUNT='//192.0.2.30/media /mnt/nas-server-jdownloader cifs credentials=/etc/jdownloader-nas/credentials,vers=2.0,uid=101000,gid=101000,forceuid,forcegid,file_mode=0660,dir_mode=0770,nosuid,nodev,noexec,_netdev,x-systemd.mount-timeout=20s 0 0'
grep -q ' /mnt/nas-server-jdownloader ' /etc/fstab || echo "$MOUNT" >> /etc/fstab
systemctl daemon-reload
mountpoint -q /mnt/nas-server-jdownloader || mount /mnt/nas-server-jdownloader
test "$(findmnt -n -o FSTYPE -T /mnt/nas-server-jdownloader)" = cifs
touch /mnt/nas-server-jdownloader/.jd2-provision-check
rm /mnt/nas-server-jdownloader/.jd2-provision-check
pct create "$CT_ID" local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname jdownloader2 --unprivileged 1 --cores 4 --memory 4096 --swap 2048 \
  --rootfs local-lvm:24 --onboot 1 --startup order=30 \
  --net0 name=eth0,bridge=vmbr0,ip=192.0.2.20/24,gw=192.0.2.1,firewall=1 \
  --nameserver 192.0.2.1 --searchdomain fritz.box \
  --mp0 /mnt/nas-server-jdownloader/Downloads,mp=/mnt/downloads,backup=0
install -d /var/lib/vz/snippets
cat > /var/lib/vz/snippets/jdownloader-nas-hook.sh <<'HOOK'
#!/bin/bash
set -euo pipefail
if [ "$2" = pre-start ]; then
  mountpoint -q /mnt/nas-server-jdownloader || mount /mnt/nas-server-jdownloader
  test "$(findmnt -n -o FSTYPE -T /mnt/nas-server-jdownloader)" = cifs
  timeout 10 stat /mnt/nas-server-jdownloader >/dev/null
fi
HOOK
chmod 700 /var/lib/vz/snippets/jdownloader-nas-hook.sh
CONTENT=$(pvesh get /storage/local --output-format json | python3 -c 'import json,sys; print(json.load(sys.stdin)["content"])')
case ",$CONTENT," in *,snippets,*) ;; *) pvesm set local --content "$CONTENT,snippets" ;; esac
pct set "$CT_ID" --hookscript local:snippets/jdownloader-nas-hook.sh
pct start "$CT_ID"
pct exec "$CT_ID" -- bash -c 'printf "Acquire::ForceIPv4 \"true\";\n" > /etc/apt/apt.conf.d/99force-ipv4; apt-get update -qq; DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openjdk-21-jre python3-venv python3-pip nginx curl ca-certificates nodejs npm nftables'
echo 'Container und NAS vorbereitet.'
