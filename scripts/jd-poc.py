#!/usr/bin/env python3
"""Real download smoke test; no simulated engine."""
import json
from pathlib import Path
import time
from urllib.parse import quote
from urllib.request import urlopen

def call(endpoint, *params):
    query = '&'.join(quote(json.dumps(p, separators=(',', ':')), safe='') for p in params)
    url = 'http://127.0.0.1:3128' + endpoint + ('?' + query if query else '')
    with urlopen(url, timeout=15) as response:
        body = json.load(response)
    return body.get('data', body) if isinstance(body, dict) else body

if __name__ == '__main__':
    print('API-Version:', call('/jd/version'))
    job = call('/linkgrabberv2/addLinks', {
        'links': 'https://installer.jdownloader.org/JDownloader.jar',
        'destinationFolder': '/mnt/downloads',
        'packageName': 'JD2-Abnahmetest',
        'autostart': True,
        'assignJobID': True,
        'overwritePackagizerRules': True,
    })
    print('Auftrag akzeptiert:', isinstance(job, dict) and 'id' in job)
    query = {k: True for k in ['bytesLoaded', 'bytesTotal', 'speed', 'eta', 'status', 'finished', 'running', 'enabled', 'host']}
    query.update({'startAt': 0, 'maxResults': -1})
    for _ in range(60):
        links = call('/downloadsV2/queryLinks', query)
        if links:
            print(json.dumps(links, ensure_ascii=False))
        if any(x.get('finished') for x in links):
            files = list(Path('/mnt/downloads').glob('**/JDownloader.jar'))
            assert files and files[0].stat().st_size > 0
            print('Echter Testdownload auf NAS erfolgreich:', files[0].name, files[0].stat().st_size)
            break
        time.sleep(2)
    else:
        print('LinkGrabber:', json.dumps(call('/linkgrabberv2/queryLinks', {'startAt':0,'maxResults':-1,'status':True,'url':True}), ensure_ascii=False))
        raise SystemExit('Testdownload nicht abgeschlossen.')
