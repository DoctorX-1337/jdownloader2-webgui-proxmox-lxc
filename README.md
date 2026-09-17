# JDownloader 2 · Custom Fan Project

Lokales Downloadportal für eine native, headless betriebene JDownloader-2-Installation in einem unprivilegierten Proxmox-LXC. Vorhandene Mockups, Logos und Favicons bilden die Gestaltung; Downloadstatus und Aktionen stammen aus der echten JDownloader-API.

Alle IP-Adressen, NAS-Namen und Containerkennungen in dieser öffentlichen Fassung sind neutrale Beispielwerte. Vor der Installation müssen sie an die eigene Umgebung angepasst werden; produktive Infrastrukturangaben und Zugangsdaten werden nicht veröffentlicht. Die Beispiele verwenden das Dokumentationsnetz `192.0.2.0/24`.

## Beispielkonfiguration

| Eigenschaft | Wert |
|---|---|
| Proxmox | 192.0.2.10 |
| Container | 200 · jdownloader2 · unprivilegiert |
| Weboberfläche | http://192.0.2.20/ |
| DNS-Namen | jdownloader2 · jdownloader.fritz.box |
| Betriebssystem | Ubuntu 24.04 LTS |
| Ressourcen | 4 vCPU · 4 GB RAM · 2 GB Swap · 24 GB Systemdisk |
| Benutzername | admin |
| Downloadziel | `\\NAS-SERVER\media\Downloads` |
| Containerpfad | `/mnt/downloads` |

Das gewünschte Zugangspasswort wurde ausschließlich über einen Argon2id-Hash eingerichtet. Es steht nicht in Quellcode oder Dokumentation. Ein Web-Setup und eine Registrierung sind deaktiviert; die Einrichtung geschieht vor Freigabe des Webservers.

Ubuntu 26.04 ist in der Vorlagenliste vorhanden, wird aber vom installierten Proxmox 9.0.3 beim Erstellen ausdrücklich als nicht unterstützt abgelehnt. Deshalb verwendet diese Installation Ubuntu 24.04 LTS. Der Container wurde anschließend aktualisiert.

## Bedienung

1. Anmelden und in der Übersicht Links einfügen; Zeilenumbrüche, Leerzeichen und Tabs werden akzeptiert.
2. **Download starten** drücken. Doppelte Links innerhalb des Auftrags werden entfernt.
3. JDownloader analysiert, bestätigt und startet verfügbare Links automatisch. Nicht verfügbare Links bleiben mit ihrem Status im LinkGrabber.
4. Fortschritt, Geschwindigkeit, ETA, Hoster, Paket und Aktionen stehen unter **Downloads**. Entfernen löscht den Listeneintrag; vorhandene Dateien bleiben erhalten.
5. **Historie** zeigt abgeschlossene Dateien auch nach dem Entfernen aus der JDownloader-Liste.

Unter **Einstellungen → NAS-Zielpfad** ist die vollständige NAS-Adresse frei änderbar, zum Beispiel `\\anderes-nas\Freigabe\Unterordner`. Benutzername und NAS-Passwort sind optional; ohne neue Anmeldung bleibt der gespeicherte NAS-Zugang erhalten. Die neue Freigabe wird zuerst gemountet und mit den tatsächlichen Container-UIDs auf Schreibbarkeit geprüft. Fehlende Unterordner werden angelegt. Danach wird Container 200 kurz neu gestartet. Bestehende Dateien bleiben am bisherigen Ort; unterbrochene Downloads können am neuen Ziel von vorn beginnen.

Unter **Einstellungen → Premium-Accounts** lassen sich unterstützte Downloadanbieter auswählen und Accounts hinzufügen, prüfen, deaktivieren oder entfernen. Manche Anbieter benötigen einen API-Schlüssel. Die Hosterliste und Accountprüfung kommen direkt von JDownloader. Das Webportal speichert keine Premium-Passwörter in SQLite und gibt sie nicht zurück.

Unter **Einstellungen → Browser-Erweiterung** stehen Pakete für Firefox und Chromium bereit. Die Erweiterung fängt Click’n’Load-Aufrufe an `127.0.0.1:9666` beziehungsweise `localhost:9666` ab und leitet sie mit einem eigenen Erweiterungsschlüssel an dieses Portal weiter. Normale Links und markierte Linklisten können zusätzlich über das Browser-Kontextmenü gesendet werden. Beim Speichern fragt der Browser einmal nach Zugriff auf die frei eingestellte Portal-Adresse. Liegt die von Mozilla signierte XPI vor, startet **In Firefox installieren** den Firefox-Installationsdialog direkt aus der WebGUI. Bis dahin steht das Entwicklerpaket für `about:debugging` bereit. Chromium lädt das entpackte Paket im Entwicklermodus; eine private Website darf Erweiterungen dort nicht direkt installieren. Der Erweiterungsschlüssel kann im Portal kopiert oder erneuert werden.

Firefox Release und Beta akzeptieren nur von Mozilla signierte Erweiterungen. Die Signierung zur Selbstverteilung benötigt einmalig AMO-API-Zugangsdaten und speichert diese nicht:

```bash
AMO_JWT_ISSUER='...' AMO_JWT_SECRET='...' bash scripts/sign-firefox-extension.sh
```

Die erzeugte XPI kommt nach `browser-extension/signed/`, wird beim nächsten Build in die WebGUI übernommen und von Nginx als `application/x-xpinstall` ausgeliefert. Danach genügt in Firefox ein Klick in der WebGUI plus die Bestätigung des Browserdialogs.

Unter **Einstellungen → Entpackpasswörter** lassen sich Standardpasswörter einzeln hinzufügen und entfernen. Das Portal zeigt nur die Anzahl an; die Werte bleiben in JDownloaders eigener geschützter Konfiguration. Ist **Neue Archive automatisch entpacken** aktiviert, probiert JDownloader diese Liste bei neu hinzugefügten ZIP-, RAR- und 7z-Aufträgen automatisch. Der Ablauf wurde mit einem verschlüsselten Testarchiv bis zur inhaltlich geprüften Datei auf dem NAS verifiziert.

Ein erfolgreich übergebener Link kann trotzdem beim Anbieter auf ein Captcha oder einen kostenlosen Downloadslot warten. Das Portal zeigt diesen Zustand deutlich an. Für unbeaufsichtigte Downloads bei solchen Anbietern ist ein gültiger Premium-Account erforderlich; aktuell ist kein Account vorinstalliert.

## Architektur

```text
Browser → Nginx :80 → FastAPI 127.0.0.1:8000
                         ↓
                JDownloader 127.0.0.1:3128
                         ↓
                  /mnt/downloads
                         ↓ Bind-Mount
     Proxmox CIFS /mnt/nas-server-jdownloader/Downloads
                         ↓
              NAS-SERVER / media / Downloads
```

JDownloader verwendet seine vorhandene lokale API, intern weiterhin „Deprecated API“ genannt. Die aktuell laufende Installation wurde mit echten Aufrufen geprüft. `autostart=true` setzt in JDownloader sowohl automatische Bestätigung als auch Start. Requests werden als JSON-POST mit nativen positionalen `params` übergeben; Zugangsdaten stehen nicht in URL-Parametern. Es wird kein MyJDownloader-Konto benötigt.

Quellen: [API-Dokumentation](https://my.jdownloader.org/developers/index.html), [RemoteAPIConfig](https://github.com/mirror/jdownloader/blob/master/src/org/jdownloader/api/RemoteAPIConfig.java), [Headless-Installation](https://support.jdownloader.org/en/knowledgebase/article/install-jdownloader-on-nas-and-embedded-devices).

## NAS-Schutz und Verwaltung

Die NAS-Anmeldung liegt mit Modus `0600` ausschließlich auf Proxmox unter `/etc/jdownloader-nas/credentials`. Die CIFS-Freigabe wird auf dem Host gemountet; ausschließlich der gewählte Zielordner wird in den Container eingebunden. UID/GID `1000:1000` im Container entsprechen `101000:101000` auf Proxmox.

Die Mountprüfung verlangt den exakten Container-Mountpoint, Dateisystem `cifs`, die konfigurierte Quelle und den tatsächlichen Unterordner aus `/proc/self/mountinfo`. Ein bloß vorhandener Ordner reicht nicht. Schreibtest und Speicherprüfung laufen unter einem Zeitlimit. Vor neuen Downloads, Fortsetzen und globalem Start wird erneut geprüft. Der systemd-Dienst prüft zusätzlich vor jedem JDownloader-Start; eine Timer-Überwachung stoppt JDownloader bei einem NAS-Ausfall.

Für die ausdrücklich freigegebene NAS-Verwaltung existiert auf Proxmox ein eigener SSH-Benutzer `jd2mount`. Sein Schlüssel ist auf `192.0.2.20` und einen festen Verwaltungshelfer für Container **200** eingeschränkt. Shell, PTY, Port-, Agent- und X11-Weiterleitung sind gesperrt. Sudo erlaubt ausschließlich den festen RPC-Wrapper ohne Argumente. Der Helfer kann NAS-Konfiguration und Bind-Mount dieses Containers ändern und ihn neu starten. Er übernimmt keine Shell-Kommandos aus Web-Eingaben. Ein fehlgeschlagener Wechsel versucht das bisherige Ziel wiederherzustellen.

Diese Anwendung braucht HTTP-Zugriff im LAN, CIFS zum NAS sowie ausgehende Verbindungen für Downloads und Updates. Backend und JDownloader-API sind nur auf Loopback erreichbar. Container-SSH und Maildienst sind deaktiviert; Verwaltung erfolgt über `pct exec` auf Proxmox. Die Container-Firewall erlaubt Webzugriff ausschließlich aus `192.0.2.0/24`.

## Reproduzierbare Installation

Die ausführliche Host-Einrichtung steht in [docs/PROXMOX.md](docs/PROXMOX.md).

1. NAS auf Proxmox mounten, unprivilegierten LXC anlegen und den gewählten NAS-Unterordner nach `/mnt/downloads` binden.
2. Projekt nach `/opt/jdownloader-web` kopieren.
3. Administrator-Hash ohne Passwortecho erstellen. Dafür zuerst `python3-venv` installieren:

```bash
python3 -m venv /opt/jdownloader-web/venv
/opt/jdownloader-web/venv/bin/pip install argon2-cffi
/opt/jdownloader-web/venv/bin/python /opt/jdownloader-web/scripts/hash-password.py /tmp/jdownloader-admin.json
chgrp 1000 /tmp/jdownloader-admin.json
bash /opt/jdownloader-web/scripts/install.sh --admin-hash-file /tmp/jdownloader-admin.json
```

Der Installer aktualisiert den Container, installiert die Laufzeit, richtet Benutzer, Dienste, Firewall und Nginx ein, baut das Frontend und prüft den Status. Ein bestehendes Administratorkonto wird nicht überschrieben. Für einen Neuaufbau müssen die NAS-Verwaltung und ihre Schlüssel auf Proxmox separat eingerichtet werden; siehe die Host-Anleitung.

## Verzeichnisse und Dienste

| Pfad/Dienst | Zweck |
|---|---|
| `/opt/jdownloader` | JDownloader, Plugins und Updater; Benutzer jdownloader |
| `/var/lib/jdownloader/cfg` | persistente JD-Konfiguration; `/opt/jdownloader/cfg` ist ein Symlink |
| `/opt/jdownloader-web` | Quellcode, Python-venv, gebaute Weboberfläche |
| `/etc/jdownloader-web/config.env` | Konfiguration, Modus 0640 |
| `/etc/jdownloader-web/nas_key` | eingeschränkter NAS-Verwaltungsschlüssel, Modus 0600 |
| `/etc/jdownloader-web/browser-extension.token` | eigener Zugriffsschlüssel der Browser-Erweiterung, Modus 0600 |
| `/var/lib/jdownloader-web/app.db` | Administrator-Hash, Sitzungen, Einstellungen, Historie |
| `jdownloader.service` | native Headless-Engine, automatischer Neustart einschließlich Updates |
| `jdownloader-web.service` | FastAPI/Uvicorn als Benutzer jdweb |
| `jdownloader-nas-watch.timer` | laufende NAS-Überwachung |
| `nginx.service` | Webserver |

## Update, Backup und Restore

Neue Projektquellen zuerst nach `/opt/jdownloader-web` kopieren, anschließend:

```bash
bash /opt/jdownloader-web/scripts/update.sh
bash /opt/jdownloader-web/scripts/backup.sh
bash /opt/jdownloader-web/scripts/restore.sh /var/backups/jdownloader-web/DATEI.tar.gz
```

Backups enthalten eine konsistente SQLite-Sicherung, Webkonfiguration einschließlich eingeschränktem Schlüssel und JDownloader-Konfiguration. Während der JD-Konfigurationssicherung wird die Engine kurz gestoppt. Downloads werden nicht kopiert. Backup-Dateien können Account-Zugangsdaten und Schlüssel enthalten und sind mit `0600` zu schützen. Proxmox-seitig zusätzlich `/etc/jdownloader-nas`, den zugehörigen fstab-Eintrag, den NAS-Hook und die LXC-Konfiguration sichern. Der Container-Backupjob schließt den NAS-Bind-Mount aus.

Restore validiert das Archiv, erstellt vorher ein Backup des aktuellen Zustands und meldet alte Sitzungen ab. Für eine exakt identische JD-Konfiguration sollte Restore auf einem passenden Container erfolgen; ein Restore ändert nicht automatisch den Host-Mount.

## Diagnose und Passwort zurücksetzen

```bash
pct exec 200 -- bash /opt/jdownloader-web/scripts/healthcheck.sh
pct exec 200 -- journalctl -u jdownloader-web -n 80 --no-pager
pct exec 200 -- journalctl -u jdownloader -n 80 --no-pager
pct exec 200 -- systemctl status jdownloader-nas-watch.timer
pct exec 200 -- ss -lntp
```

Passwort in einer interaktiven Proxmox-Konsole zurücksetzen:

```bash
pct enter 200
cd /opt/jdownloader-web/backend
PYTHONPATH=/opt/jdownloader-web/backend /opt/jdownloader-web/venv/bin/python ../scripts/reset-password.py
```

Weitere Hinweise: [Troubleshooting](docs/TROUBLESHOOTING.md), [Sicherheit](docs/SECURITY.md), [Abnahme](docs/ACCEPTANCE.md).

## Entwicklung

Backend-Abhängigkeiten stehen in `backend/requirements.txt`, Frontend-Abhängigkeiten in `frontend/package-lock.json`. Produktionsdaten, private Schlüssel, die ursprünglichen Zugangsanweisungen und die Passwortdatei sind von Git und Quellpaketen ausgeschlossen.

```bash
python -m pytest tests -q
cd frontend
npm ci
npm run build
```

Tests verwenden eigene Stubs ausschließlich in den Testdateien. Die ausgelieferte Anwendung enthält keinen simulierten Downloadbetrieb. Die isolierte Browserprüfung und Live-Tests lesen die lokal vorhandene Passwortdatei direkt; diese Hilfen gehören nicht zum Webserver.

Unofficial Custom Fan Project. Not affiliated with or endorsed by the JDownloader developers. Die bereitgestellten Bilddateien bleiben vom Software-Lizenztext ausgenommen; deren Rechte liegen bei den jeweiligen Rechteinhabern.
