# Proxmox-Einrichtung

## Konkrete Konfiguration

Host `192.0.2.10`, Container `200`, IP `192.0.2.20/24`, Gateway/DNS `192.0.2.1`, Bridge `vmbr0`, Hostname `jdownloader2`, Suchdomäne `fritz.box`. Ressourcen: 4 Kerne, 4096 MB RAM, 2048 MB Swap, 24 GB auf `local-lvm`, Autostart und unprivilegiert.

Proxmox 9.0.3 unterstützt die angebotene Ubuntu-26.04-Vorlage noch nicht. Die tatsächliche Installation verwendet Ubuntu 24.04 LTS. Keine bestehenden Container oder Host-Pakete für diesen Versionswechsel aktualisieren.

## NAS-Mount

Pakete `cifs-utils`, `smbclient` und `sudo` auf dem Host voraussetzen bzw. installieren. NAS-Zugangsdaten in `/etc/jdownloader-nas/credentials` schreiben, ohne sie in Shell-Historie oder Befehlsargumente zu setzen:

```bash
install -d -m 700 /etc/jdownloader-nas
editor /etc/jdownloader-nas/credentials
chmod 600 /etc/jdownloader-nas/credentials
install -d -m 000 /mnt/nas-server-jdownloader
```

Die Credentials-Datei enthält die CIFS-Schlüssel `username` und `password`; tatsächliche Werte werden hier bewusst nicht aufgeführt. Bestehende Credentials dürfen für eine Neuinstallation aus einem autorisierten lokalen Mount übernommen werden.

Aktueller fstab-Eintrag:

```fstab
//192.0.2.30/media /mnt/nas-server-jdownloader cifs credentials=/etc/jdownloader-nas/credentials,vers=2.0,uid=101000,gid=101000,forceuid,forcegid,file_mode=0660,dir_mode=0770,nosuid,nodev,noexec,_netdev,x-systemd.mount-timeout=20s 0 0
```

Die vorhandene NAS-Freigabe unterstützt in dieser Umgebung SMB 2.0. Der Web-Verwaltungshelfer probiert bei einem Zielwechsel zunächst neuere SMB-Versionen. **Kein `prefixpath=Downloads` verwenden:** Diese Option wurde in der vorhandenen Mount-Implementierung ignoriert. Stattdessen immer den vorhandenen Unterordner explizit binden.

```bash
systemctl daemon-reload
mount /mnt/nas-server-jdownloader
findmnt /mnt/nas-server-jdownloader
ls -ld /mnt/nas-server-jdownloader/Downloads
```

Den Modus `000` nur auf dem ungemounteten lokalen Verzeichnis setzen. Ein chmod auf einem aktiven CIFS-Mount kann Eigenschaften des NAS-Ordners verändern.

## Container anlegen

```bash
pveam update
pveam download local ubuntu-24.04-standard_24.04-2_amd64.tar.zst
pct create 200 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname jdownloader2 --unprivileged 1 --cores 4 --memory 4096 --swap 2048 \
  --rootfs local-lvm:24 --onboot 1 --startup order=30 \
  --net0 name=eth0,bridge=vmbr0,ip=192.0.2.20/24,gw=192.0.2.1,firewall=1 \
  --nameserver 192.0.2.1 --searchdomain fritz.box \
  --mp0 /mnt/nas-server-jdownloader/Downloads,mp=/mnt/downloads,backup=0
```

Falls der Host keine IPv6-Verbindung besitzt und `pveam download` dennoch IPv6 wählt, die aktuelle Vorlage mit `wget -4` vom Proxmox-Downloadserver nach `/var/lib/vz/template/cache` laden. Verfügbarkeit und Prüfsumme der Vorlage vor Neuinstallation prüfen.

Der Projekt-Hook `/var/lib/vz/snippets/jdownloader-nas-hook.sh` prüft vor `pre-start` einen aktiven CIFS-Mount. Er mountet ihn bei Bedarf und lehnt den Containerstart bei nicht erreichbarem NAS ab. Auf Speicher `local` muss zusätzlich Inhaltstyp `snippets` aktiviert sein; vorhandene Inhaltstypen erhalten.

```bash
pct set 200 --hookscript local:snippets/jdownloader-nas-hook.sh
pct start 200
```

`scripts/provision-host.sh` bildet die konkrete vorhandene Umgebung ab. Es lehnt eine belegte Container-ID oder antwortende Ziel-IP ab und übernimmt NAS-Credentials aus der vorhandenen autorisierten media-Konfiguration in Container 201. Für einen anderen Proxmox-Host diesen Übernahmeschritt an dessen NAS-Anmeldung anpassen.

## Anwendung installieren

Projekt nach `/opt/jdownloader-web` kopieren, dann die Schritte in der README ausführen. Java wird als vollständiges JRE installiert; der Ausführungsmodus von JDownloader bleibt headless. Benutzer `jdownloader` und Gruppe müssen exakt UID/GID `1000:1000` verwenden. Benutzer `jdweb` verwendet UID 1001 und dieselbe Gruppe.

## NAS-Einstellung aus dem Web

Die aktuelle Host-Verwaltung ist ausdrücklich vom Benutzer freigegeben. Auf einem neuen Host benötigt sie ebenfalls eine bewusste Einrichtung:

1. Ed25519-Schlüsselpaar ausschließlich für NAS-Verwaltung erzeugen. Privater Schlüssel nach `/etc/jdownloader-web/nas_key`, Eigentümer `jdweb:jdownloader`, Modus `0600`.
2. Proxmox-Hostschlüssel verifizieren und unter `/etc/jdownloader-web/nas_known_hosts` hinterlegen. `StrictHostKeyChecking=yes` bleibt aktiviert.
3. Root-eigenen Helfer `scripts/nas_host.py` nach `/usr/local/lib/jdownloader-nas/nas_host.py` kopieren; fester Wrapper `/usr/local/sbin/jd2-nas-rpc` startet ausschließlich diesen Helfer.
4. Benutzer `jd2mount` mit gesperrtem Passwort und Shell `/bin/sh` anlegen. Sein Home und `.ssh` bleiben root-eigen und für seine Gruppe nur lesbar.
5. `authorized_keys` enthält einen auf `from="192.0.2.20"` und `command="sudo -n /usr/local/sbin/jd2-nas-rpc"` eingeschränkten Schlüssel mit `no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty`.
6. Sudoers erlaubt nur `jd2mount ALL=(root) NOPASSWD: /usr/local/sbin/jd2-nas-rpc ""`; mit `visudo -cf` prüfen.
7. `scripts/setup-nas-admin.sh` automatisiert diese Schritte für die aktuelle Umgebung. Es erwartet die vorbereiteten privaten Dateien unter `/tmp`; diese Dateien danach entfernen.

Es wird kein Proxmox-Rootpasswort im Container gespeichert. Der Helfer akzeptiert JSON für `status` und `configure`, arbeitet nur an den festen Projektpfaden und Container 200 und übergibt Benutzereingaben ausschließlich als Daten an Systemwerkzeuge. Nach erfolgreicher Probe startet ein zeitversetzter Host-Job den Mountwechsel und Container-Neustart.

## DNS und HTTPS

Die Installation verwendet den geprüften Namen **http://jdownloader2/** und die IP `192.0.2.20`. Der ursprünglich gewünschte Alias `jdownloader.fritz.box` ist im Router nicht vorhanden; für diese Installation wurde die Verwendung von `jdownloader2` bestätigt. Nginx akzeptiert den zusätzlichen Alias weiterhin, falls er später im lokalen DNS eingetragen wird. Ein LXC-Hostname allein erzeugt bei statischer IP keinen garantierten Fritz-DNS-Eintrag.

HTTPS ist über `nginx/https.example.conf` vorbereitet. Ein vertrauenswürdiges internes Zertifikat installieren, Port 443 aktivieren, `COOKIE_SECURE=true` setzen und Webdienst neu starten.

## Backup

Container-Backup ohne NAS-Daten; der Bind-Mount ist mit `backup=0` markiert. Zusätzlich auf Proxmox sichern:

- `/etc/pve/lxc/200.conf`
- `/etc/jdownloader-nas/` einschließlich geschützter NAS-Anmeldung
- den einzelnen Projekt-Eintrag aus `/etc/fstab`
- `/var/lib/vz/snippets/jdownloader-nas-hook.sh`
- `/usr/local/lib/jdownloader-nas/nas_host.py`, RPC-Wrapper und eingeschränkte Benutzer-/SSH-/sudo-Konfiguration

Host-Backups enthalten Geheimnisse und müssen separat geschützt werden.
