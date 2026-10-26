# JDownloader 2 · Custom Fan Project

**Unofficial Self-Hosted Web Interface for JDownloader 2**

Eine moderne, selbst gehostete Weboberfläche zur Verwaltung von **JDownloader 2** in einem unprivilegierten **Proxmox-LXC-Container**.

Das Projekt verbindet die native Download-Engine mit einer eigenständigen WebGUI, zentraler NAS-Anbindung und komfortablen Verwaltungsfunktionen. Im Mittelpunkt stehen eine übersichtliche Bedienung, nachvollziehbare Statusanzeigen und ein zuverlässiger Downloadbetrieb – ohne erforderliches MyJDownloader-Konto.

> **Hinweis:** Dies ist ein unabhängiges, inoffizielles Fanprojekt und keine Anwendung der JDownloader-Entwickler.

## Funktionen im Überblick

| Bereich | Funktionen |
|---|---|
| **Downloadverwaltung** | Links hinzufügen, analysieren, starten, pausieren, fortsetzen und entfernen |
| **Live-Monitoring** | Paket- und Dateifortschritt, Geschwindigkeit, übertragene Daten und Restzeit |
| **LinkGrabber & DLC** | Linksammlungen, Mehrfachauswahl und Upload von DLC-Containern |
| **Entpacken** | Automatische und manuelle Archivverarbeitung, Passwortverwaltung und eigener Entpackstatus |
| **NAS-Integration** | SMB-/CIFS-Speicherziel, Schreibprüfung, Ausfallüberwachung und Zielpfadverwaltung |
| **Browser-Integration** | Click'n'Load sowie Linkübergabe über Firefox- und Chromium-Erweiterungspakete |
| **Premium-Accounts** | Verwaltung unterstützter Downloadanbieter über die WebGUI |
| **Administration** | Lokaler Administratorzugang, Diagnose, Updates, Backup und Restore |

Die WebGUI verwendet **echte Status- und Aktionsdaten aus der lokalen JDownloader-API**. Es werden keine Downloads simuliert und keine unbekannten Fortschrittswerte erfunden.

## Schnellinstallation auf Proxmox VE

Für die Einrichtung steht ein interaktiver Installationsassistent bereit. Er wird in der **Root-Konsole des gewünschten Proxmox-VE-Knotens** ausgeführt.

Installationsskript herunterladen:

```bash
curl --proto '=https' --tlsv1.2 -fsSL \
  https://raw.githubusercontent.com/DoctorX-1337/jdownloader2-webgui-proxmox-lxc/main/scripts/quick-install.sh \
  -o jd2-quick-install.sh
```

Das heruntergeladene Skript vor der Ausführung prüfen und anschließend starten:

```bash
bash jd2-quick-install.sh
```

Der Assistent führt durch die erforderlichen Einstellungen und richtet unter anderem Folgendes ein:

1. Einen neuen unprivilegierten Ubuntu-LXC-Container
2. Netzwerk und NAS-Anbindung
3. Die native JDownloader-2-Engine im Headless-Betrieb
4. Backend, Weboberfläche und Nginx
5. Einen eigenen Administratorzugang
6. Benötigte Dienste und NAS-Überwachung

Passwörter werden bei der Eingabe verdeckt. Bestehende Container werden nicht automatisch übernommen.

Im **Schnellmodus** werden die nächste freie Container-ID, ein freier Name (`jdownloader2`, danach `jdownloader2-01`, `-02` usw.), Storage, Bridge und Ressourcen automatisch gewählt. Gateway, DNS und Proxmox-Adresse werden erkannt. Für individuelle Einstellungen steht **Eigene Vorgaben** bereit. Der Assistent verarbeitet Konsoleneingaben und Kommandoausgaben mit festgelegter UTF-8-Codierung.

**Ausführliche Anleitung:** [Schnellinstallation](docs/QUICK-INSTALL.md)

## Die Weboberfläche

### Downloads und Pakete

Neue Links können direkt im Browser eingefügt und an JDownloader übergeben werden. Die Downloadansicht bietet sowohl eine **Paketübersicht** als auch eine **Einzeldateiansicht**.

Angezeigt werden – soweit von der Engine verfügbar – der Gesamtfortschritt, einzelne Dateifortschritte, übertragene Datenmengen, Geschwindigkeit, verbleibende Zeit, Hoster und Downloadzustand. Die Werte aktualisieren sich automatisch.

Aktive Downloads erhalten animierte Fortschrittsanzeigen. Pausierte, wartende, fehlerhafte und abgeschlossene Downloads werden passend zu ihrem Zustand dargestellt. Die Einstellung `prefers-reduced-motion` wird berücksichtigt.

Mehrere Links beziehungsweise Downloadaufträge lassen sich auswählen und nach ausdrücklicher Bestätigung entfernen. Bereits heruntergeladene Dateien bleiben dabei erhalten.

### Archive und Entpacken

Der separate Bereich **Entpacken** zeigt erkannte Archive, heruntergeladene und fehlende Teile sowie den tatsächlichen Entpackfortschritt. Je nach Archivzustand stehen Aktionen zum Starten, erneuten Entpacken oder Abbrechen zur Verfügung.

Unterstützt werden außerdem Standardpasswörter für Archive und die automatische Verarbeitung neuer ZIP-, RAR- und 7z-Aufträge. Passwortfehler, Prüfsummenfehler und fehlende Archivteile werden gesondert angezeigt.

### LinkGrabber, DLC und Browser-Erweiterungen

Die WebGUI unterstützt die Linkanalyse über JDownloader sowie den Upload mehrerer `.dlc`-Dateien nach einer ausdrücklichen Bestätigung. Die enthaltenen Links werden anschließend durch JDownloader verarbeitet.

Für **Firefox** und **Chromium** stehen Erweiterungspakete zur Verfügung. Sie ermöglichen unter anderem Click'n'Load, die Übergabe von Links und markierten Linklisten sowie die Konfiguration der Portaladresse.

Bei Firefox ist für die reguläre Installation eine von Mozilla signierte Erweiterung erforderlich; für Chromium wird das entpackte Erweiterungspaket im Entwicklermodus eingebunden.

### NAS-Anbindung und Schutzmechanismen

Die SMB-/CIFS-Freigabe wird auf dem Proxmox-Host eingebunden. Nur der vorgesehene Downloadordner wird an den unprivilegierten Container durchgereicht.

Der **NAS-Wächter** prüft Verfügbarkeit und Schreibbarkeit des Speicherziels. Bei einem Ausfall stoppt er den Downloadbetrieb, damit JDownloader nicht unbeabsichtigt in einen lokalen Ersatzordner schreibt.

Sobald das NAS und die lokale Engine-API wieder bereitstehen, kann ein zuvor aktiver Downloadbetrieb fortgesetzt werden. Absichtlich angehaltene oder pausierte Downloads bleiben angehalten.

Der Zielpfad lässt sich über die Einstellungen der WebGUI ändern. **Wichtig:** Dateien am bisherigen Speicherort werden nicht automatisch verschoben; unterbrochene Downloads können am neuen Ziel erneut beginnen müssen.

## Technische Architektur

```text
Browser
   |
   v
Nginx (Port 80)
   |
   v
FastAPI / Uvicorn (127.0.0.1:8000)
   |
   v
JDownloader 2 API (127.0.0.1:3128)
   |
   v
/mnt/downloads (LXC)
   |
   v
Proxmox-Bind-Mount -> SMB/CIFS-Freigabe -> NAS
```

| Komponente | Technologie |
|---|---|
| Virtualisierung | Proxmox VE |
| Laufzeitumgebung | Unprivilegierter Ubuntu-LXC |
| Webserver | Nginx |
| Backend | Python / FastAPI |
| Download-Engine | JDownloader 2 (Headless) |
| Datenbank | SQLite |
| Netzwerkfreigabe | SMB / CIFS |
| Anmeldung | Lokaler Administratorzugang mit Argon2id-Passworthashing |

Die JDownloader-API und das Backend sind nur über Loopback erreichbar. Die Bedienung erfolgt über die WebGUI; ein MyJDownloader-Konto ist für diese Integration nicht notwendig.

## Voraussetzungen

- Proxmox VE mit Unterstützung für unprivilegierte LXC-Container
- Eine mit der Proxmox-Version kompatible Ubuntu-LXC-Vorlage
- Netzwerkzugriff für Installation, Downloads und Aktualisierungen
- Eine erreichbare SMB-/CIFS-Freigabe, wenn Downloads auf einem NAS gespeichert werden sollen
- Ausreichend CPU, Arbeitsspeicher und Speicherplatz entsprechend dem geplanten Downloadbetrieb

Die im Projekt dokumentierte Installation nutzt **Ubuntu 24.04 LTS**. Ob andere Vorlagen verwendet werden können, hängt unter anderem von der eingesetzten Proxmox-Version ab.

## Sicherheit

Die Anwendung enthält mehrere Schutzmaßnahmen:

- Unprivilegierter Container und getrennte Dienstbenutzer
- Passwort-Hashing mit Argon2id
- Sitzungsbasierte Anmeldung und CSRF-Schutz
- Geschützte Speicherung von Zugangsdaten und Schlüsseln
- Beschränkung von Backend und JDownloader-API auf Loopback
- Eingeschränkte Host-Verwaltung für NAS-Änderungen
- Überwachung des NAS-Mounts vor und während des Downloadbetriebs

**Netzwerkhinweis:** Die Standard-Weboberfläche ist für den Zugriff innerhalb eines vertrauenswürdigen lokalen Netzwerks vorgesehen. Für Zugriff von außen sollte ein entsprechend abgesicherter **HTTPS-Reverse-Proxy** verwendet werden. Die Herkunftsprüfung und die Konfiguration vertrauenswürdiger Proxy-Adressen sind dabei zu berücksichtigen.

Weitere Informationen: [Sicherheitsdokumentation](docs/SECURITY.md)

## Wartung, Backup und Diagnose

| Aufgabe | Skript |
|---|---|
| Installation | `scripts/install.sh` |
| Aktualisierung | `scripts/update.sh` |
| Backup | `scripts/backup.sh` |
| Wiederherstellung | `scripts/restore.sh` |
| Diagnose | `scripts/healthcheck.sh` |
| Administratorpasswort zurücksetzen | `scripts/reset-password.py` |

Die Backup-Funktion sichert die relevante Anwendungs- und JDownloader-Konfiguration, **nicht** die heruntergeladenen Dateien. Sicherungsarchive können Zugangsdaten enthalten und müssen entsprechend geschützt werden.

Für die detaillierte manuelle Einrichtung siehe [Proxmox-Installation](docs/PROXMOX.md).

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [Schnellinstallation](docs/QUICK-INSTALL.md) | Interaktive Einrichtung und Voraussetzungen |
| [Proxmox-Installation](docs/PROXMOX.md) | Host-Konfiguration und manuelle Installation |
| [Sicherheit](docs/SECURITY.md) | Schutzmechanismen, Zugangsdaten und Netzwerk |
| [Fehlerbehebung](docs/TROUBLESHOOTING.md) | Diagnose und bekannte Fehlerfälle |
| [Abnahme](docs/ACCEPTANCE.md) | Funktionsprüfungen und Tests |

## Hinweise und Grenzen

- Verfügbarkeit und Geschwindigkeit hängen vom jeweiligen Downloadanbieter ab.
- Captchas, Wartezeiten und kostenlose Downloadslots werden nicht umgangen.
- Manche Anbieter benötigen für unbeaufsichtigte Downloads einen gültigen Premium-Account.
- Die WebGUI ersetzt nicht die JDownloader-Engine, sondern steuert sie über deren API.
- Installation und Betrieb setzen grundlegende Kenntnisse im Umgang mit Proxmox und Linux voraus.

## Rechtlicher Hinweis

**JDownloader 2 · Custom Fan Project** ist ein unabhängiges, inoffizielles Fanprojekt und steht in keiner offiziellen Verbindung zu den Entwicklern von JDownloader. Es wird von diesen weder entwickelt noch offiziell unterstützt oder empfohlen.

JDownloader und zugehörige Produktbezeichnungen sind Eigentum ihrer jeweiligen Rechteinhaber. Die Rechte an eingebundenen Logos, Marken und Bilddateien verbleiben bei den jeweiligen Rechteinhabern und werden nicht durch eine gegebenenfalls vorhandene Softwarelizenz dieses Projekts übertragen.
