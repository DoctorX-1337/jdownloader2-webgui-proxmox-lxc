# Fehlerdiagnose

## NAS offline

Downloads bleiben blockiert. Auf Proxmox:

```bash
findmnt /mnt/nas-server-jdownloader
timeout 10 stat /mnt/nas-server-jdownloader/Downloads
pct exec 200 -- timeout 12 runuser -u jdownloader -- python3 /usr/local/lib/jdownloader/check-nas.py
```

Nach einem Zielwechsel den tatsächlich konfigurierten Unterordner verwenden. Host-Credentials nicht in Ausgaben kopieren. Erst NAS-Verbindung wiederherstellen; lokale Ersatzordner nicht für den Downloadbenutzer freigeben.

Falls der Container mit nicht verfügbarem NAS nicht startet, ist das beabsichtigt: der `pre-start`-Hook lehnt ihn ab. Freigabe wieder verbinden, dann `pct start 200`.

## NAS-Wechsel fehlgeschlagen

Eine nicht erreichbare neue Freigabe wird bereits in der Probe verworfen. Der bisherige Mount bleibt erhalten. Falls der spätere Wechsel scheitert, versucht der Host-Job einen Rollback. Status und Nachricht stehen unter Einstellungen; ergänzend:

```bash
cat /etc/jdownloader-nas/state.json
journalctl --since '10 minutes ago' --no-pager | grep jd2-nas-apply
pct status 200
```

Die State-Datei enthält Zielpfad und Status, keine Passwörter. Bei einem fehlgeschlagenen Rollback NAS-Mount, `mp0` und `config.env` in der Proxmox-Konsole abgleichen. Unvollständige Downloads am neuen Ziel benötigen eventuell einen Neustart.

## JDownloader offline

```bash
pct exec 200 -- systemctl status jdownloader
pct exec 200 -- journalctl -u jdownloader -n 80 --no-pager
pct exec 200 -- curl -fsS http://127.0.0.1:3128/jd/version
```

Beim ersten Start lädt der Updater Komponenten und startet die Engine mehrfach neu. Der Service nutzt `-norestart` mit `Restart=always`, damit systemd Neustarts und Updates überwacht. Ein vollständiges JRE wird benötigt, auch bei headless Ausführung.

## Link nicht verfügbar

LinkGrabber zeigt den echten Anbieterstatus. Eine erfolgreiche Übergabe bedeutet, dass JDownloader den Auftrag erhalten hat; sie bestätigt nicht, dass jeder Anbieter einen Download ermöglicht. Offline-Links werden nicht als fertige Downloads dargestellt. Captchas und Browser-Challenges gehören nicht zur ersten Version.

## Premium-Account

**Einstellungen → Premium-Accounts**. Exakte unterstützte Anbieter-Domain aus der Liste wählen. Je nach Anbieter Benutzername/E-Mail und Passwort oder API-Schlüssel verwenden. Nach dem Hinzufügen prüft JDownloader den Account. „Neu prüfen“ aktualisiert den echten Anbieterstatus. Provider-Zugangsdaten nicht mit dem Seitenpasswort verwechseln.

## Nginx/Backend

```bash
pct exec 200 -- nginx -t
pct exec 200 -- journalctl -u jdownloader-web -n 80 --no-pager
pct exec 200 -- bash /opt/jdownloader-web/scripts/healthcheck.sh
```

Kurzzeitige 502 während eines Neustarts können auftreten. Dauerhafte 502: Backend-Dienst und Python-venv prüfen. Bei CSRF-Fehler die Seite neu laden. Nach fünf fehlgeschlagenen Logins 15 Minuten warten. Passwortreset steht in der README.

## DNS

Wenn die IP funktioniert, aber der Name nicht, den lokalen DNS-Eintrag prüfen. Nginx akzeptiert die vorgegebenen Namen bereits. Fritz-/AdGuard-DNS muss beide Namen auf die Container-IP auflösen.
