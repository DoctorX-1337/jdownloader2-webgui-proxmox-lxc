"""Exercise real downloads against a temporary, independently hosted fixture."""
from pathlib import Path
import sys
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def main():
    client = requests.Session()
    client.trust_env = False
    base = 'http://192.0.2.20/api'
    password = (ROOT/'zugangspasswort wunsch.txt').read_text(encoding='utf-8-sig').strip()
    login = client.post(base+'/auth/login', json={'username':'admin','password':password}, timeout=15)
    login.raise_for_status()
    headers = {'X-CSRF-Token':login.json()['csrf']}
    def call(method, path, **kwargs):
        response = client.request(method, base+path, headers=headers, timeout=20, **kwargs)
        response.raise_for_status()
        return response.json()
    previous = call('GET','/settings')
    try:
        hosts = call('GET','/accounts/hosts')
        assert 'rapidgator.net' in hosts and len(hosts)>100
        assert isinstance(call('GET','/accounts'),list)
        rejected = client.post(base+'/accounts', headers=headers, json={'host':'unsupported.invalid','username':'fixture-user','password':'fixture-only-value'}, timeout=15)
        assert rejected.status_code==422 and 'fixture-only-value' not in rejected.text
        print('Premium-Anbieter und Ablehnung eines unbekannten Anbieters bestanden.')
        call('PUT','/settings',json={**previous,'speed_limit':128,'parallel':2,'chunks':1,'autostart':True})
        links=[f'http://192.0.2.10:18765/JD2-Abnahme-{i}.bin' for i in range(1,6)]
        job=call('POST','/downloads',json={'links':'\n'.join(links+[links[0]])})
        assert job['submitted']==5
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            rows=[r for r in call('GET','/downloads')['links'] if r['name'].startswith('JD2-Abnahme-')]
            if len(rows)==5 and any(r.get('bytesLoaded',0)>0 for r in rows):break
            time.sleep(1)
        assert len(rows)==5 and any(r.get('bytesLoaded',0)>0 for r in rows)
        ident=next(r['uuid'] for r in rows if not r.get('finished'))
        call('POST',f'/downloads/{ident}/pause')
        assert not next(r for r in call('GET','/downloads')['links'] if r['uuid']==ident)['enabled']
        call('POST',f'/downloads/{ident}/resume')
        assert next(r for r in call('GET','/downloads')['links'] if r['uuid']==ident)['enabled']
        call('POST','/controller/pause')
        assert 'PAUSE' in call('GET','/downloads')['state']
        call('POST','/controller/start')
        call('POST',f'/downloads/{ident}/retry')
        print('Fünf echte Downloads, Deduplizierung, Pause, Fortsetzen und Neustart bestanden.',flush=True)
        call('PUT','/settings',json={**previous,'speed_limit':0,'parallel':2,'chunks':1,'autostart':True})
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            rows=[r for r in call('GET','/downloads')['links'] if r['name'].startswith('JD2-Abnahme-')]
            if len(rows)==5 and all(r.get('finished') for r in rows):break
            time.sleep(2)
        assert len(rows)==5 and all(r.get('finished') for r in rows)
        time.sleep(6)
        history=call('GET','/downloads/history')
        assert all(any(h['name']==r['name'] for h in history) for r in rows)
        for row in rows:call('DELETE','/downloads/'+row['uuid'])
        assert not any(r['name'].startswith('JD2-Abnahme-') for r in call('GET','/downloads')['links'])
        print('Alle fünf Dateien abgeschlossen, Historie vorhanden, Listeneinträge entfernt.')
    finally:
        call('PUT','/settings',json=previous)
        call('POST','/auth/logout')

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('Downloadprüfung fehlgeschlagen:',type(error).__name__)
        sys.exit(1)
