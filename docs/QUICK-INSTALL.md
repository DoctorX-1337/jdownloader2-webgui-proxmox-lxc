# Proxmox VE: Schnellinstallation

Der Assistent erstellt einen neuen unprivilegierten Ubuntu-24.04-LXC auf einem Proxmox-VE-8- oder -9-Knoten mit amd64. Er richtet NAS-Mount, Startschutz, JDownloader, WebGUI, Administrator, Firewall und den auf diesen Container begrenzten NAS-Verwaltungszugang ein. Beim Start erscheint das mitgelieferte ASCII-Logo.

In der **interaktiven root-Konsole des gewünschten Proxmox-Knotens** ausführen:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/DoctorX-1337/jdownloader2-webgui-proxmox-lxc/main/scripts/quick-install.sh -o jd2-quick-install.sh
bash jd2-quick-install.sh
```

Der Assistent lädt die Projektquellen aus diesem Repository. Das Skript vor dem Start nach Bedarf ansehen. Für eine bestimmte Version kann `JD2_REF` auf eine vollständige Git-Commit-ID gesetzt werden; standardmäßig wird `main` verwendet.

```bash
# Nur Werkzeuge prüfen, ohne Container oder Mount anzulegen:
bash jd2-quick-install.sh --check
```

Standard ist **Schnellinstallation**: Die nächste freie Container-ID kommt von Proxmox. Der Hostname wird clusterweit geprüft; bei vorhandenem `jdownloader2` folgen automatisch `jdownloader2-01`, `-02` usw. Systemdisk-Storage, Template-Storage, Bridge, Gateway, DNS, Proxmox-Adresse und Ressourcen werden vorbelegt. Abgefragt werden die freie statische IPv4-Adresse samt Präfix, der SMB-Zielpfad und die Anmeldedaten. **Eigene Vorgaben** erlaubt die Anpassung aller Werte.

NAS- und WebGUI-Passwort werden verdeckt abgefragt und nicht ausgegeben. Vor der ersten Änderung erscheint eine Zusammenfassung aller Werte zur Bestätigung. Der WebGUI-Benutzer heißt `admin`; sein Passwort benötigt mindestens zwölf Zeichen. Das Startskript setzt eine UTF-8-Umgebung; ungültige Zeichen aus der Konsole führen zu einer erneuten Eingabe statt zu einem unverständlichen Decoder-Abbruch.

Als Standard sind 4 vCPU, 4 GiB RAM, 2 GiB Swap und eine 24-GiB-Systemdisk vorgesehen. Der LXC benötigt Internetzugang für Ubuntu-Pakete, npm, Python und die JDownloader-Engine. Ein aktiver Directory-Storage für das NAS-Hookskript muss vorhanden sein. Der Assistent ergänzt dort gegebenenfalls den Inhaltstyp `snippets`. Der Proxmox-Knoten muss aus dem LXC auf TCP-Port 22 erreichbar sein. Die WebGUI-Firewall erlaubt HTTP/HTTPS aus dem eingegebenen IPv4-Subnetz; für andere Clientnetze muss die Regel später angepasst werden.

Die SMB-Freigabe muss SMB 3 unterstützen und für den angegebenen Benutzer schreibbar sein. Sie wird auf dem Host unter `/mnt/bindmounts/jd2-<CTID>` gemountet und im Container als `/mnt/downloads` eingebunden. Eine vorhandene Freigabe kann einen Unterordner enthalten. Zugangsdaten liegen nur in der rootgeschützten Datei `/etc/jdownloader-nas/<CTID>/credentials`. Die Berechtigungsprüfung verwendet die tatsächlich zugeordneten Container-IDs. Ein NAS-Ausfall blockiert den Containerstart beziehungsweise neue Downloads.

Nach erfolgreicher Prüfung zeigt der Assistent die Webadresse und den Benutzernamen. Einen DNS-Namen im eigenen Router/DNS auf die Container-IP setzen. Premium-Accounts, Entpackpasswörter und Browser-Erweiterung werden anschließend in der WebGUI eingerichtet. Firefox Release benötigt weiterhin eine von Mozilla signierte XPI.

Bestehende Gäste und belegte Installationspfade werden abgelehnt. Ein fehlgeschlagener Lauf löscht keinen Container und keine NAS-Dateien automatisch; angelegte Ressourcen bleiben zur Diagnose erhalten. Zugangsdaten werden nie als Kommandozeilenargumente übergeben. Der NAS-Verwaltungsschlüssel erlaubt nur den spezifischen Verwaltungshelfer dieses LXC, keine freie Shell und keine Weiterleitungen. Ein späterer NAS-Wechsel über Einstellungen startet ausschließlich diesen Container kurz neu.

Host-Mount, Hookskript und Verwaltungshelfer gelten für den Installationsknoten. Vor einer späteren Migration müssen diese auf dem Zielknoten eingerichtet und die Verwaltungsadresse angepasst werden. Der NAS-Inhalt des Bind-Mounts ist nicht Teil eines normalen Container-Backups. Das entspricht den [Proxmox-Hinweisen zu Bind-Mounts](https://github.com/proxmox/pve-docs/blob/master/pct.adoc#bind-mount-points).

Diese Schnellinstallation ist für neue Installationen vorgesehen. Bestehende Installationen verwenden den beschriebenen Updateweg im README.
