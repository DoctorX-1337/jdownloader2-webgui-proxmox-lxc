import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from backend.app import main, database, auth

class ClientStub:
    async def aclose(self): pass

class Engine:
    client=ClientStub()
    def __init__(self):self.calls=[]
    async def call(self,path,*params):
        self.calls.append((path,params))
        if path=='/linkgrabberv2/addLinks':return {'id':1234567890123}
        return True

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(database,'DATA',tmp_path)
    monkeypatch.setattr(database,'DATABASE',tmp_path/'test.db')
    engine=Engine()
    monkeypatch.setattr(main,'jd',engine)
    async def monitor():await asyncio.Event().wait()
    monkeypatch.setattr(main,'monitor',monitor)
    async def online():return {'online':True,'writable':True,'free':10**12,'total':2*10**12}
    monkeypatch.setattr(main,'storage',online)
    with TestClient(main.app) as client:
        with database.db() as db:
            db.execute('INSERT INTO users VALUES (?,?)',('admin',auth.hasher.hash('test-only-password-123')))
        yield client,engine

def signed_in(client):
    response=client.post('/api/auth/login',json={'username':'admin','password':'test-only-password-123'})
    assert response.status_code==200
    return {'X-CSRF-Token':response.json()['csrf']}

def test_authentication_csrf_and_logout(client):
    browser,engine=client
    assert browser.get('/api/downloads').status_code==401
    headers=signed_in(browser)
    assert 'HttpOnly' in browser.cookies.jar._cookies['testserver.local']['/']['jd_session']._rest
    assert browser.post('/api/controller/start').status_code==403
    assert browser.post('/api/controller/start',headers={**headers,'Origin':'http://attacker.example'}).status_code==403
    assert not engine.calls
    assert browser.post('/api/auth/logout',headers=headers).status_code==200
    assert browser.get('/api/auth/session').status_code==401

def test_multiple_links_are_deduplicated_and_real_engine_called(client):
    browser,engine=client
    headers=signed_in(browser)
    response=browser.post('/api/downloads',headers=headers,json={'links':'https://example.org/a.zip\nhttps://example.org/b.zip\thttps://example.org/a.zip'})
    assert response.status_code==200
    assert response.json()['submitted']==2
    endpoint,params=engine.calls[0]
    assert endpoint=='/linkgrabberv2/addLinks'
    assert params[0]['links']=='https://example.org/a.zip\nhttps://example.org/b.zip'
    assert params[0]['destinationFolder']=='/mnt/downloads'
    assert params[0]['autostart'] is True

def test_offline_nas_blocks_new_download_and_resume(client,monkeypatch):
    browser,engine=client
    headers=signed_in(browser)
    async def offline():return {'online':False,'writable':False,'free':0,'total':0}
    monkeypatch.setattr(main,'storage',offline)
    assert browser.post('/api/downloads',headers=headers,json={'links':['https://example.org/a.zip']}).status_code==503
    assert browser.post('/api/downloads/42/resume',headers=headers).status_code==503
    assert browser.post('/api/controller/start',headers=headers).status_code==503
    assert not engine.calls

def test_engine_failure_does_not_report_success(client,monkeypatch):
    browser,engine=client
    headers=signed_in(browser)
    async def unavailable(*args):raise main.EngineUnavailable()
    monkeypatch.setattr(engine,'call',unavailable)
    response=browser.post('/api/downloads',headers=headers,json={'links':['https://example.org/a.zip']})
    assert response.status_code==503
    assert 'success' not in response.json()

def test_invalid_link_never_reaches_engine(client):
    browser,engine=client
    headers=signed_in(browser)
    for value in ['file:///etc/passwd','https://name:password@example.org/a.zip','hello; touch /tmp/a','javascript:alert(1)']:
        assert browser.post('/api/downloads',headers=headers,json={'links':value}).status_code==422
    assert not engine.calls

def test_login_throttling_and_no_secret_echo(client):
    browser,engine=client
    for _ in range(5):
        response=browser.post('/api/auth/login',json={'username':'admin','password':'incorrect-private-value'})
        assert response.status_code==401
        assert 'incorrect-private-value' not in response.text
    assert browser.post('/api/auth/login',json={'username':'admin','password':'test-only-password-123'}).status_code==429
    response=browser.post('/api/auth/login',json={'username':'admin','password':{'private':'no-output'}})
    assert response.status_code==422
    assert 'no-output' not in response.text

def test_password_change_revokes_existing_sessions(client):
    browser,engine=client
    headers=signed_in(browser)
    previous=browser.cookies.get('jd_session')
    response=browser.post('/api/auth/password',headers=headers,json={'old_password':'test-only-password-123','new_password':'replacement-test-password-123'})
    assert response.status_code==200
    browser.cookies.set('jd_session',previous)
    assert browser.get('/api/auth/session').status_code==401

def test_pause_retry_remove_have_actual_api_calls(client):
    browser,engine=client
    headers=signed_in(browser)
    assert browser.post('/api/downloads/42/pause',headers=headers).status_code==200
    assert engine.calls[0]==('/downloadsV2/setEnabled',(False,[42],[]))
    assert browser.post('/api/downloads/42/retry',headers=headers).status_code==200
    assert ('/downloadsV2/resetLinks',([42],[])) in engine.calls
    assert browser.delete('/api/downloads/42',headers=headers).status_code==200
    assert engine.calls[-1]==('/downloadsV2/removeLinks',([42],[]))

def test_premium_account_credentials_are_not_returned_or_saved(client,monkeypatch):
    browser,engine=client
    headers=signed_in(browser)
    async def call(path,*params):
        engine.calls.append((path,params))
        if path=='/accountsV2/listPremiumHosterUrls':return {'premium.example':'https://premium.example'}
        if path=='/accountsV2/listAccounts':return [{'uuid':42,'hostname':'premium.example','username':'test-user','password':'not-for-the-browser','enabled':True,'valid':False}]
    monkeypatch.setattr(engine,'call',call)
    response=browser.post('/api/accounts',headers=headers,json={'host':'premium.example','username':'test-user','password':'private-premium-test-value'})
    assert response.status_code==200
    assert 'private-premium-test-value' not in response.text
    assert ('/accountsV2/addAccount',('premium.example','test-user','private-premium-test-value')) in engine.calls
    response=browser.get('/api/accounts')
    assert 'not-for-the-browser' not in response.text
    with database.db() as db:
        assert db.execute('SELECT COUNT(*) FROM settings').fetchone()[0]==0

def test_zero_speed_limit_disables_limit_without_setting_invalid_zero(client):
    browser,engine=client
    headers=signed_in(browser)
    response=browser.put('/api/settings',headers=headers,json={'parallel':3,'chunks':2,'speed_limit':0,'autostart':True,'auto_extract':True})
    assert response.status_code==200
    assert not any(call[1][2]=='DownloadSpeedLimit' for call in engine.calls)
    assert ('/config/set',('org.jdownloader.settings.GeneralSettings',None,'DownloadSpeedLimitEnabled',False)) in engine.calls
