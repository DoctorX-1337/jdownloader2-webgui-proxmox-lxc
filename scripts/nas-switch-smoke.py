from pathlib import Path
import sys
import time
import requests

ROOT=Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

def main():
    c=requests.Session();c.trust_env=False;base='http://192.0.2.20/api'
    secret=(ROOT/'zugangspasswort wunsch.txt').read_text(encoding='utf-8-sig').strip()
    response=c.post(base+'/auth/login',json={'username':'admin','password':secret},timeout=15)
    assert response.status_code==200
    headers={'X-CSRF-Token':response.json()['csrf'],'Origin':'http://192.0.2.20'}
    action=sys.argv[1]
    if action=='configure':
        target=sys.argv[2]
        response=c.put(base+'/settings/nas',headers=headers,json={'target':target},timeout=95)
        print('NAS-Wechsel HTTP:',response.status_code)
        if response.status_code!=200:
            print('Ergebnis:',response.json().get('detail','fehlgeschlagen'));raise SystemExit(1)
        print('Neues NAS wurde geprüft; Wechsel wurde beauftragt.')
    elif action=='wait':
        expected=sys.argv[2]
        for _ in range(50):
            try:
                response=c.get(base+'/settings/nas',timeout=5)
                state=response.json()
                health=c.get(base+'/health',timeout=5).json()
                if state.get('status')=='ready' and state.get('target')==expected and health.get('nas')==health.get('jdownloader')=='online':
                    system=c.get(base+'/system/status',timeout=5).json()
                    assert system['nasPath'].replace('192.0.2.30','NAS-SERVER')==expected
                    print('NAS-Wechsel und Wiederanlauf vollständig bestätigt.');break
                if state.get('status')=='error':print('NAS-Wechsel:',state.get('message'));raise SystemExit(1)
            except (requests.RequestException,ValueError):pass
            time.sleep(2)
        else:raise SystemExit(1)
    elif action=='invalid':
        previous=c.get(base+'/settings/nas',timeout=15).json()['target']
        response=c.put(base+'/settings/nas',headers=headers,json={'target':r'\\192.0.2.30\JD2-NichtVorhandeneFreigabe\Downloads'},timeout=95)
        assert response.status_code==422
        assert c.get(base+'/settings/nas',timeout=15).json()['target']==previous
        assert c.get(base+'/health',timeout=15).json()['nas']=='online'
        print('Nicht vorhandene NAS-Freigabe abgewiesen; bisheriges Ziel ist weiterhin online.')

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('NAS-Test fehlgeschlagen:',type(error).__name__);sys.exit(1)
