# Abnahme vom 13. September 2026

Geprüft am tatsächlich laufenden Proxmox-LXC 200 und mit einer isolierten Chrome-Sitzung. Die Webanwendung verwendet die echte lokale JDownloader-API.

| Prüfung | Ergebnis |
|---|---|
| Backend- und NAS-Tests | 18 bestanden; zwei Deprecation-Warnungen der Testbibliotheken |
| Produktionsbuild | TypeScript-Prüfung und Vite-Build erfolgreich |
| Anmeldung und Abmeldung | Gewünschtes Passwort funktioniert; HttpOnly-Sitzung, Abmeldung sperrt die Sitzung |
| CSRF und fremde Origins | Änderungen ohne gültigen CSRF-Token oder mit fremder Origin werden abgewiesen |
| Passwortänderung | Automatisierter Test bestätigt Widerruf alter Sitzungen |
| Webdarstellung | Login, Übersicht und Einstellungen in Chrome geprüft; Desktop und 390-Pixel-Smartphone ohne horizontales Überlaufen |
| Mehrfachdownload | Fünf eigene Dateien über die Web-API an JDownloader übergeben und automatisch vollständig heruntergeladen |
| Doppelte Links | Sechs Eingabezeilen mit einer Wiederholung ergeben fünf übergebene Links |
| Steuerung | Einzelpause, Fortsetzen, globale Pause, Start und erneuter Download praktisch erfolgreich |
| Dateien auf NAS | Alle fünf Dateien über den unabhängigen media-Mount geprüft; Größe und SHA-256 stimmen |
| Historie und Entfernen | Abgeschlossene Dateien erscheinen in der Historie; Entfernen löscht die JD-Listeneinträge |
| NAS-Zielwechsel | Wechsel in einen anderen Unterordner samt Container-Neustart und Rückwechsel erfolgreich |
| Ungültige Freigabe | Wird abgewiesen; bestehendes NAS-Ziel bleibt verfügbar |
| Fehlender NAS-Mount | Vorübergehend ausschließlich CT 200 auf einen leeren, nicht beschreibbaren Ersatz-Bind-Mount gesetzt |
| Ausfallschutz | NAS und JD werden offline angezeigt; neue Downloads, globaler Start und Fortsetzen liefern HTTP 503; Watchdog stoppt JD |
| Wiederanlauf | Original-Bind-Mount wiederhergestellt; JD, Webserver und NAS starten wieder erfolgreich |
| Premium-Integration | 715 reale Anbieter abrufbar, Accountliste erreichbar, unbekannter Anbieter ohne Passwortecho abgewiesen |
| Premium-Geheimnisse | Tests bestätigen POST-Übertragung ohne URL-Geheimnisse, keine Passwortrückgabe und keine Speicherung in der Web-Datenbank |
| Datenbank | SQLite `integrity_check` erfolgreich |
| Backup | Echtes Archiv erstellt; SQLite darin konsistent, Archivmodus 0600 |
| Wiederherstellung | Derselbe gesicherte Zustand praktisch wiederhergestellt; anschließender Healthcheck erfolgreich |
| Frontend-Abhängigkeiten | `npm audit --omit=dev`: keine gemeldeten Schwachstellen |
| Festgeschriebene Python-Pakete | PyPI meldet für die verwendeten direkten Paketversionen keine Schwachstellen |
| Netzwerk | Nginx für das LAN erreichbar; JD-API und FastAPI nur auf Loopback; SSH und Postfix im Container deaktiviert |
| DNS | `jdownloader2` löst auf 192.0.2.20 auf und ist der bestätigte Zugangsname |

Die selbst erzeugten Testdateien, Testaufträge und Testhistorie wurden anschließend entfernt; der temporäre Download-Testserver wurde beendet.

Ein tatsächlicher Premium-Login beim Anbieter konnte ohne dessen Zugangsdaten nicht geprüft werden. JDownloader übernimmt diese Prüfung nach dem Hinzufügen im Portal. Die Installation verwendet HTTP im lokalen Netz; HTTPS ist als separate Konfigurationsvorlage vorbereitet. Die Sicherheitsabfragen der Paketregister sind eine Bestandsaufnahme zum Prüftermin.

Private Anweisungen, Passwortdatei, produktive Datenbank, Backups, Hash-Dateien und SSH-Schlüssel werden nicht veröffentlicht.
