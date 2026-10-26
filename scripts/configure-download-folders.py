#!/usr/bin/env python3
"""Configure package folders through the live loopback API; no engine restart."""
import json
import os
import urllib.request


def call(endpoint, *params):
    request = urllib.request.Request(
        'http://127.0.0.1:' + str(int(os.getenv('JD_PORT', '3128'))) + endpoint,
        data=json.dumps({'params':list(params)}).encode(),
        headers={'Content-Type':'application/json'},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.load(response)
    if 'type' in body:
        raise RuntimeError('JDownloader-Konfiguration konnte nicht geändert werden.')
    return body.get('data')


def configure():
    settings = [
        ('org.jdownloader.settings.GeneralSettings', None, 'DefaultDownloadFolder', '/mnt/downloads/<jd:packagename>'),
        ('org.jdownloader.extensions.extraction.ExtractionConfig', 'cfg/org.jdownloader.extensions.extraction.ExtractionExtension', 'CustomExtractionPathEnabled', False),
        ('org.jdownloader.extensions.extraction.ExtractionConfig', 'cfg/org.jdownloader.extensions.extraction.ExtractionExtension', 'SubpathEnabled', False),
    ]
    for interface, storage, key, value in settings:
        if not call('/config/set', interface, storage, key, value):
            raise RuntimeError('Paketordner-Einstellung wurde nicht bestätigt.')
    print('Neue Pakete verwenden eigene Unterordner; Entpacken bleibt standardmäßig im Paketordner.')


if __name__ == '__main__':
    configure()
