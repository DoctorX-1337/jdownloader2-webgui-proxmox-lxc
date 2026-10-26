# Entpacken, Paketordner und Proxmox-Schnellinstallation

## Verhalten

Der eigene Tab **Entpacken** zeigt JDownloaders Archivkatalog mit echten Status- und Fortschrittswerten. Start, Neustart und Abbruch erfordern eine Bestätigung. Aktionen werden vor dem Aufruf erneut gegen den nativen Katalog geprüft und auf die exakten Archivteile beziehungsweise den aktuellen Controller begrenzt. Fehlende Teile und mehrdeutige Dateinamen sperren den manuellen Start. Ein Neustart setzt ausschließlich den archivbezogenen Entpackpfad auf einen neuen Unterordner; bestehende Dateien und globale Passwort-/Löschregeln bleiben erhalten.

Neue normale Links, DLC-Aufträge, Click’n’Load und manuell gestartete LinkGrabber-Aufträge verwenden benannte Paketordner. Das Konfigurationsskript setzt dieselbe Vorgabe über die lokale API ohne Engine-Neustart. Die optionale Bestandsmigration verwendet JDownloaders Verschiebefunktion für Archive und einen protokollierten, nicht überschreibenden Rename für eindeutig zugeordnete entpackte Dateien. Laufende und teilweise geladene Pakete bleiben unverändert.

Die Schnellinstallation erstellt einen neuen unprivilegierten LXC auf Proxmox VE 8/9. Der interaktive Assistent zeigt das ASCII-Logo, fragt die Konfiguration ab, richtet SMB, WebGUI und einen auf diesen LXC beschränkten NAS-Verwaltungszugang ein und prüft den Dienststatus. Er übernimmt keine Zugangsdaten anderer Container. Bestehende Gast-IDs und Installationspfade werden abgelehnt. Details: [Schnellinstallation](QUICK-INSTALL.md).

Der NAS-Wächter merkt sich den Downloadcontroller-Zustand vor seinem Schutzstopp. Nach Rückkehr des NAS wartet er auf die lokale API und nimmt einen zuvor laufenden Downloadbetrieb wieder auf. Ein absichtlich angehaltener oder pausierter Controller wird nicht gestartet. Der Wiederherstellungsmarker bleibt auch bei Stop-Timeouts und längeren Engine-Updates erhalten.

## Prüfung

- 99 Python-Tests: bisherige Funktionen, Paketpfade, Pfadbereinigung, Archivzuordnung, genaue IDs, Bestätigungen/CSRF, Neustartziel, Abbruch, unvollständige und veraltete Aufträge, Installationsgrenzen und Controller-Wiederaufnahme.
- Isolierter Shell-Test: fehlgeschlagener NAS-Schutzstopp, vorhandener Marker, verzögerte API-Bereitschaft und erfolgreicher späterer Wiederanlauf.
- TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich.
- Browserprüfung in Chromium auf Desktop und Mobilformat: automatische Prozentaktualisierung, Modalbestätigung, Abbrechen ohne Aktion, Archiv-Neustart und Abbruch, gesperrte unvollständige Archive, kein horizontaler Seitenüberlauf. Schreibende Browser-Testaktionen wurden abgefangen.
- Echter nativer Archivkatalog, Paketziele, NAS-Schreibbarkeit, laufender Downloadcontroller und tatsächlicher Datentransfer geprüft. Web-Update und Einbau der Wiederaufnahme ohne Engine-Neustart.
- Installationsskripte auf Bash-Syntax geprüft; `--check` auf einem echten Proxmox-Knoten erfolgreich. Kein zusätzlicher vollständiger LXC-Neuaufbau für die Abnahme. Firefox wurde nicht als eigener Browser-Testlauf verwendet.

Produktive Zugangsdaten, Konfigurationen, Schlüssel, private Journale und Browser-Testhilfen gehören nicht in das Repository.
