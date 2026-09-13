"""Live API checks. Read the password from its private input, never print it."""
from pathlib import Path
import sys
import requests

ROOT=Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

def main():
    client=requests.Session()
    client.trust_env=False
    base='http://192.0.2.20/api'
    assert client.get(base+'/auth/session',timeout=10).status_code==401
    password=(ROOT/'zugangspasswort wunsch.txt').read_text(encoding='utf-8-sig').strip()
    response=client.post(base+'/auth/login',json={'username':'admin','password':password},timeout=15)
    assert response.status_code==200
    headers={'X-CSRF-Token':response.json()['csrf'],'Origin':'http://192.0.2.20'}
    assert client.post(base+'/controller/start',timeout=15).status_code==403
    for path in ['/health','/downloads','/linkgrabber','/downloads/history','/system/status','/settings','/settings/nas']:
        result=client.get(base+path,timeout=20)
        print(path,result.status_code)
        assert result.status_code==200
    prefs=client.get(base+'/settings',timeout=15).json()
    assert client.put(base+'/settings',json=prefs,headers=headers,timeout=20).status_code==200
    print('JDownloader-Einstellungen: gelesen und unverändert erfolgreich gespeichert.')
    target=client.get(base+'/settings/nas',timeout=15).json()
    print('NAS-Verwaltung:',target['status'])
    assert client.post(base+'/auth/logout',headers=headers,timeout=10).status_code==200
    assert client.get(base+'/auth/session',timeout=10).status_code==401
    print('Live-API-Prüfung einschließlich Login, CSRF und Logout bestanden.')

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('Live-Prüfung fehlgeschlagen:',type(error).__name__)
        sys.exit(1)
