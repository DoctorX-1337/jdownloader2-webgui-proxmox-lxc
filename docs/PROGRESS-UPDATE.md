# Paketfortschritt, dynamische Ladebalken und Mehrfachauswahl

## Verhalten

- Paketansicht mit echten JDownloader-Gesamtwerten, gewichteten Byte-Fortschritten, fertigen Teilen, Geschwindigkeit und Restzeit. Die Einzeldateiansicht bleibt erreichbar.
- Gemeinsame Fortschrittskomponente für Pakete, Dateien und kompakte Dateidetails. Keine neue Animationsbibliothek und keine simulierten Downloadwerte.
- Deutlich sichtbarer Schimmer von rechts nach links, dezente diagonale Lichtstreifen, pulsierende Kante und drei kleine Partikel. Effekte laufen nur bei gemessenem Datentransfer, sichtbarer Anzeige und sichtbarem Tab. Pause, Fehler, Stillstand, Abschluss und Bewegungsreduzierung bleiben statisch.
- Eigener Entpackfortschritt unter dem Downloadbalken: native Prozentwerte, verarbeitete Bytes, Gesamtgröße, Status und Restzeit des aktuellen Archivs. Ein fertig geladener Download wird weiterhin als 100 % angezeigt; der Entpackvorgang besitzt einen eigenen Wert. Doppelte Controller-Meldungen auf mehreren RAR-Teilen werden nicht aufsummiert.
- Mehrfachauswahl und „Alle auswählen“ im LinkGrabber und in der Einzeldateiansicht. Entfernen verlangt eine gesonderte Bestätigung mit Anzahl und Bereich. Nur ausgewählte IDs werden übergeben; NAS-Dateien werden nicht gelöscht.
- Neu hinzukommende Einträge werden nicht automatisch ausgewählt. Filter und automatische Aktualisierung erhalten die Auswahl. Fehlgeschlagene Entfernungen erhalten die verbleibende Auswahl.
- Bei einem Verbindungsfehler bleibt der letzte Paketstand sichtbar und wird als veraltet gekennzeichnet.

## Geänderte Dateien

Backend:

- `backend/app/main.py`
- `backend/app/jd.py`
- `backend/app/packages.py`
- `backend/app/extraction.py`

Frontend:

- `frontend/src/main.tsx`
- `frontend/src/PackageDownloads.tsx`
- `frontend/src/packages.css`
- `frontend/src/DownloadProgress.tsx`
- `frontend/src/download-progress.css`
- `frontend/src/ExtractionStatus.tsx`
- `frontend/src/BulkSelection.tsx`
- `frontend/src/bulk-selection.css`
- `frontend/src/LinkGrabber.tsx`

Prüfungen und Dokumentation:

- `tests/test_backend.py`
- `tests/test_packages.py`
- `tests/test_jd_transport.py`
- `tests/test_extraction_progress.py`
- `tests/test_nas_watch_recovery.sh`
- `scripts/nas-watch.sh`
- `README.md`
- `docs/PROGRESS-UPDATE.md`

## Durchgeführte Prüfungen

- 66 automatisierte Python-Tests erfolgreich: Authentifizierung, CSRF, Paketwerte, unbekannte Größen, Pausen, große IDs, Entpackdaten, bestätigte Auswahl, ungültige IDs und Schutz vor unbeabsichtigten Teiländerungen.
- TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich.
- Browserprüfung in Chromium für Desktop und Smartphone ohne horizontales Überlaufen oder JavaScript-Fehler.
- Fortschrittszustände mit 0 %, größeren Sprüngen, Zurücksetzen, Pause/Fortsetzen, Geschwindigkeit null, Abschluss, Fehler und Stoppen geprüft. Keine künstliche Erhöhung oder lokale Countdown-Simulation.
- 66 gleichzeitige Anzeigen geprüft; Animationen außerhalb des sichtbaren Bereichs werden ausgesetzt. Fortschrittsupdates erhalten die DOM-Knoten.
- `prefers-reduced-motion` sowie tatsächliche Schimmerrichtung und erhöhte Deckkraft geprüft.
- Paketansicht mit echten Live-Daten und automatischen Aktualisierungen geprüft; offene Dateidetails bleiben erhalten. Verbindungsausfall und anschließende Wiederherstellung mit browserinternen Testantworten geprüft.
- Entpackfortschritt aus echten nativen Messwerten ausgelesen und mit gesondertem Balken dargestellt. Millisekunden der nativen Entpack-ETA werden in Sekunden umgerechnet.
- Einzel-/Mehrfachauswahl, Alle auswählen, Abbrechen, Bestätigung, Filter, zwischenzeitlich neue Einträge und Fehler bei der Entfernung geprüft. Sämtliche Lösch- und Steuerungsanfragen dieser Browser-Zustandstests wurden lokal abgefangen; keine echten Einträge wurden dafür entfernt.
- Isolierter Shell-Test für den NAS-Wiederanlauf erfolgreich.

## Grenzen und Betriebshinweise

- Die Gruppierung folgt JDownloader-Paketen. Ein DLC kann mehrere Pakete enthalten; der ursprüngliche DLC-Dateiname ist für ältere Einträge nicht zuverlässig rekonstruierbar.
- Zeigt ein Paket mehrere Archive, bezieht sich der Entpackbalken auf ein natives aktuelles Archiv, nicht auf eine erfundene Summe oder einen Mittelwert. Ohne native Messwerte wird keine Prozentzahl erfunden.
- Eine dauerhafte DLC-Datei-Duplikathistorie wurde nicht hinzugefügt. Innerhalb eines Uploads werden identische Container dedupliziert; spätere Link-Duplikate unterliegen JDownloaders eigener Prüfung und Einstellung.
- Die visuelle Browserabnahme erfolgte in Chromium. Ein separater nativer Firefox-Test und ein langfristiger Hardware-FPS-Benchmark wurden nicht durchgeführt.
- Während der Live-Abnahme stoppte der bestehende NAS-Schutzwächter die Engine. Der NAS-Schreibzugriff wurde erneut geprüft und der Betrieb regulär wiederhergestellt. Die Wiederanlaufmarkierung wird jetzt vor einem möglicherweise blockierenden Stopp gesetzt, damit ein Timeout den späteren Wiederanlauf nicht verhindert. Der NAS-Schutz wurde nicht abgeschaltet.

Technische Grundlage für die Entpackwerte: [JDownloader ExtractionProgress](https://github.com/mirror/jdownloader/blob/master/src/org/jdownloader/extensions/extraction/ExtractionProgress.java) und [Downloads API](https://github.com/mirror/jdownloader/blob/master/src/org/jdownloader/api/downloads/v2/DownloadsAPIV2Impl.java).
