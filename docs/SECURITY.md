# Sicherheit

## Zugang

Ein vorkonfigurierter Administrator, keine Registrierung, kein offenes Setup. Argon2id für das Seitenpasswort. Sitzungs-ID als zufälliger Wert im HttpOnly-/SameSite-Strict-Cookie; SQLite speichert nur dessen SHA-256-Hash. Jede schreibende authentifizierte Anfrage verlangt einen CSRF-Token; fremde Origins werden abgewiesen. Fünf erfolglose Anmeldeversuche je IP in 15 Minuten lösen eine Sperre aus. Passwortänderung und Restore widerrufen Sitzungen.

HTTP ist wie angefordert für das private LAN eingerichtet. Für verschlüsselte Browserübertragung ein intern vertrauenswürdiges HTTPS-Zertifikat einrichten und `COOKIE_SECURE=true` aktivieren. Das Webportal darf nicht per Portweiterleitung ins Internet veröffentlicht werden.

## Prozesse und Ports

LXC unprivilegiert. JDownloader unter UID 1000; Webdienst unter UID 1001. Beide sind eigene Benutzer, root führt nur Installation und Mountüberwachung aus. Uvicorn ist an `127.0.0.1:8000` gebunden, die lokale JDownloader-API an `127.0.0.1:3128` und Click’n’Load an `127.0.0.1:9666`. JD-interne Zusatzdienste bleiben ebenfalls auf Loopback. LAN-Eingang ausschließlich Webports 80/443 aus `192.0.2.0/24`; Container-SSH ist deaktiviert.

## NAS

Ein leerer lokaler Ordner wird nie als NAS erkannt. Exakter Mountpoint, Quelle, CIFS-Typ und Mount-Unterordner sind notwendig. Danach erfolgen ein temporärer Schreibtest und Speicherprüfung. Neue Downloads sowie Start/Fortsetzen werden bei fehlendem NAS abgewiesen. systemd verhindert den Engine-Start ohne NAS; eine Überwachung stoppt sie beim Ausfall. Der darunterliegende lokale Pfad bleibt nicht beschreibbar für die Downloadbenutzer.

Der NAS-Einstellungshelfer auf Proxmox besitzt notwendige Rootrechte, ist jedoch auf Container 200 und feste Projektpfade begrenzt. Der dedizierte SSH-Schlüssel erlaubt nur diesen festen Helfer, stammt nur von der Container-IP und erlaubt keine Shell oder Weiterleitungen. Private Schlüssel und Credentials bleiben mit `0600` geschützt. Ein Administrator kann damit ausdrücklich das gesamte NAS-Ziel einschließlich Anbieter und Zugang ändern.

## Eingaben und Geheimnisse

URLs werden als Daten an JDownloader übergeben. Kein `shell=True`, `os.system` oder Shell-Befehl aus Web-Eingaben. NAS-Pfade werden komponentenweise validiert; Pfadtraversal, Kontrollzeichen und symbolische Zielpfade werden verworfen. CIFS-Credentials laufen über eine geschützte Datei statt Mount-Befehlsargumente. JDownloader-Requests nutzen JSON-POST; Premium-Zugangsdaten stehen nicht in URLs und nicht in der Web-Datenbank. Accountstatus liefert keine Passwörter zurück und zeigt nur kategorisierte Fehler.

Die Webanwendung gibt keine Eingabewerte aus Validierungsfehlern zurück. Nginx protokolliert keine API-Zugriffe; App-Logs enthalten Statuswechsel und Auftragsanzahl, keine Zugangsdaten. JDownloader verwaltet seine Account-Konfiguration und Provider-Diagnose selbst. Seine Konfiguration und Backups grundsätzlich als geheim behandeln.

Die Browser-Erweiterung besitzt einen zufälligen, vom Administrator widerrufbaren Schlüssel. Dieser erlaubt ausschließlich das Einreichen von Links und Click’n’Load-Daten; er gewährt keinen Zugriff auf Downloads, Einstellungen, Accounts oder Administratorsitzungen. Click’n’Load wird nur an den festen Loopback-Port des Containers weitergegeben. Die Erweiterung beobachtet ausschließlich POST-Ziele auf `localhost:9666` und `127.0.0.1:9666`; für die frei eingestellte Portal-Adresse fordert sie beim Speichern eine eigene, auf diesen Ursprung begrenzte Berechtigung an. Der Schlüssel liegt im Container und im lokalen Browserprofil und gehört nicht in Supportausgaben oder Git.

Standardpasswörter für Archive werden direkt in JDownloaders `PasswordList` gespeichert. Die Web-API gibt ausschließlich ihre Anzahl zurück; auch Logs und die Web-Datenbank enthalten die Werte nicht. JDownloader-Konfigurationsbackups enthalten diese Liste und sind daher vertraulich.

Keine Geheimnisse in Git oder Quellpaketen: ursprüngliche Anweisungen/Zugangsdateien, Passwortwunsch, `.private`, `.env`, Datenbanken und private Schlüssel sind ausgeschlossen. Test- und Browserhilfen dürfen keine Exception-Details mit ausgefüllten Passwörtern drucken.
