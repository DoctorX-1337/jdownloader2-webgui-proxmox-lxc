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

## Download wartet auf Captcha

Der Status „Captcha erforderlich“ bedeutet, dass Portal, NAS und JDownloader funktionieren, der Downloadanbieter aber eine interaktive Freigabe verlangt. Unter **Einstellungen → Premium-Accounts** einen gültigen Account für die angezeigte Anbieter-Domain hinterlegen und anschließend den Download erneut versuchen. Ohne Premium-Account kann ein Headless-Download bei diesem Anbieter auf dem Captcha-Slot stehen bleiben.

## Link nicht verfügbar

LinkGrabber zeigt den echten Anbieterstatus. Eine erfolgreiche Übergabe bedeutet, dass JDownloader den Auftrag erhalten hat; sie bestätigt nicht, dass jeder Anbieter einen Download ermöglicht. Offline-Links werden nicht als fertige Downloads dargestellt.

## Browser-Erweiterung

Im Portal unter **Einstellungen → Browser-Erweiterung** in Firefox **In Firefox installieren** wählen und den Browserdialog bestätigen. Ist die Schaltfläche noch nicht verfügbar, fehlt die Mozilla-signierte XPI; bis zur Signierung kann das Entwicklerpaket temporär über `about:debugging` geladen werden. Portal-Adresse `http://jdownloader2` und den kopierten Erweiterungsschlüssel speichern und Firefox den einmalig angefragten Zugriff auf diese Adresse erlauben. Die Verbindung wird dabei ohne Download getestet. Bei `NetworkError when attempting to fetch resource` zuerst das aktuelle Paket neu laden; Version 1.0.2 fordert die benötigte Portalberechtigung an und unterbindet das automatische HTTPS-Upgrade für das lokale HTTP-Portal. Nach einer Schlüsselerneuerung müssen alle Browser den neuen Wert erhalten.

## Archive werden nicht entpackt

Unter **Einstellungen → Downloads** muss „Neue Archive automatisch entpacken“ für den neuen Auftrag aktiv gewesen sein. Ein benötigtes Passwort unter **Entpackpasswörter** hinzufügen. Mehrteilige Archive werden erst nach vollständigem Download aller Teile entpackt. Das Portal zeigt Passwörter absichtlich nicht wieder an.

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
