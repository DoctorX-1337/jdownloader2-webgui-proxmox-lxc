#!/bin/bash
set -euo pipefail
getent group jdownloader >/dev/null || groupadd --gid 1000 jdownloader
test "$(getent group jdownloader | cut -d: -f3)" = 1000 || groupmod --gid 1000 jdownloader
id jdownloader >/dev/null 2>&1 || useradd --system --uid 1000 --gid jdownloader --home-dir /var/lib/jdownloader --shell /usr/sbin/nologin jdownloader
install -d -o jdownloader -g jdownloader /opt/jdownloader /var/lib/jdownloader /var/lib/jdownloader/cfg
install -d /usr/local/lib/jdownloader
install -m 755 /tmp/check-nas.py /usr/local/lib/jdownloader/check-nas.py
test -e /opt/jdownloader/cfg || ln -s /var/lib/jdownloader/cfg /opt/jdownloader/cfg
cat > /var/lib/jdownloader/cfg/org.jdownloader.api.RemoteAPIConfig.json <<'JSON'
{"deprecatedapienabled":true,"deprecatedapilocalhostonly":true,"deprecatedapiport":3128,"headlessmyjdownloadermandatory":false,"externinterfaceenabled":false,"jdanywhereapienabled":false}
JSON
cat > /var/lib/jdownloader/cfg/org.jdownloader.settings.GeneralSettings.json <<'JSON'
{"defaultdownloadfolder":"/mnt/downloads","maxsimultanedownloads":3,"maxchunksperfile":2}
JSON
cat > /var/lib/jdownloader/cfg/org.jdownloader.extensions.extraction.ExtractionExtension.json <<'JSON'
{"enabled":true,"defaultdownloadfolder":"/mnt/downloads","customextractionpathenabled":false}
JSON
chown -R jdownloader:jdownloader /var/lib/jdownloader /opt/jdownloader
curl -4 -fsSL --retry 3 https://installer.jdownloader.org/JDownloader.jar -o /opt/jdownloader/JDownloader.jar
chown jdownloader:jdownloader /opt/jdownloader/JDownloader.jar
install -m 644 /tmp/jdownloader.service /etc/systemd/system/jdownloader.service
systemctl daemon-reload
systemctl enable --now jdownloader
echo 'JDownloader Bootstrap gestartet.'
