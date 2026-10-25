import asyncio
import base64
import json
import pytest
from fastapi.testclient import TestClient
from backend.app import main, database, auth, extension_auth

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
    token_file=tmp_path/'extension.token'
    token_file.write_text('test-extension-token-1234567890x',encoding='ascii')
    monkeypatch.setattr(extension_auth,'EXTENSION_TOKEN_FILE',token_file)
    main.recent_cnl.clear()
    with TestClient(main.app) as client:
        with database.db() as db:
            db.execute('INSERT INTO users VALUES (?,?)',('admin',auth.hasher.hash('test-only-password-123')))
        yield client,engine

def signed_in(client):
    response=client.post('/api/auth/login',json={'username':'admin','password':'test-only-password-123'})
    assert response.status_code==200
    return {'X-CSRF-Token':response.json()['csrf']}

def dlc_file(name='example.dlc', marker=b'A'):
    return {'name':name,'content':base64.b64encode(marker*128).decode('ascii')}

def test_dlc_batch_uses_normal_download_settings_and_deduplicates(client):
    browser,engine=client
    headers=signed_in(browser)
    with database.db() as connection:
        connection.execute('INSERT INTO settings VALUES (?,?)',('autostart','false'))
        connection.execute('INSERT INTO settings VALUES (?,?)',('auto_extract','false'))
    first,second=dlc_file(),dlc_file('second.DLC',b'B')
    response=browser.post('/api/downloads/dlc',headers=headers,json={'confirmed':True,'files':[first,second,first]})
    assert response.status_code==200
    assert response.json()['submitted']==2
    assert len(engine.calls)==1
    path,(query,)=engine.calls[0]
    assert path=='/linkgrabberv2/addLinks'
    assert query['dataURLs']==['data:application/dlc;base64,'+item['content'] for item in (first,second)]
    assert query['destinationFolder']=='/mnt/downloads'
    assert query['autostart'] is False and query['autoExtract'] is False
    assert query['assignJobID'] and query['overwritePackagizerRules']
    assert first['content'] not in response.text

def test_dlc_requires_session_csrf_and_explicit_confirmation(client):
    browser,engine=client
    payload={'confirmed':True,'files':[dlc_file()]}
    assert browser.post('/api/downloads/dlc',json=payload).status_code==401
    headers=signed_in(browser)
    assert browser.post('/api/downloads/dlc',json=payload).status_code==403
    assert browser.post('/api/downloads/dlc',headers={**headers,'Origin':'https://attacker.example'},json=payload).status_code==403
    for confirmation in (None,False):
        body={'files':[dlc_file()]}
        if confirmation is not None:body['confirmed']=confirmation
        assert browser.post('/api/downloads/dlc',headers=headers,json=body).status_code==422
    assert not engine.calls

@pytest.mark.parametrize('files',[
    [], [dlc_file()]*21, [dlc_file('wrong.zip')], [dlc_file('../escape.dlc')],
    [{'name':'empty.dlc','content':''}], [{'name':'bad.dlc','content':'???'}],
    [{'name':'text.dlc','content':base64.b64encode(b'not a container').decode('ascii')}],
    [dlc_file(),{'name':'bad.dlc','content':'???'}],
    [{'name':'large.dlc','content':base64.b64encode(b'A'*(2*1024*1024+1)).decode('ascii')}],
])
def test_invalid_dlc_batch_never_reaches_engine(client,files):
    browser,engine=client
    response=browser.post('/api/downloads/dlc',headers=signed_in(browser),json={'confirmed':True,'files':files})
    assert response.status_code==422
    assert not engine.calls

def test_dlc_limits_total_decoded_size_and_streamed_body(client,monkeypatch):
    browser,engine=client
    headers=signed_in(browser)
    monkeypatch.setattr(main.dlc,'MAX_TOTAL_BYTES',200)
    payload={'confirmed':True,'files':[dlc_file(),dlc_file('second.dlc',b'B')]}
    assert browser.post('/api/downloads/dlc',headers=headers,json=payload).status_code==413
    monkeypatch.setattr(main.dlc,'MAX_REQUEST_BYTES',100)
    assert browser.post('/api/downloads/dlc',headers=headers,content=iter([b' '*60,b' '*60])).status_code==413
    assert not engine.calls

def test_dlc_is_blocked_by_offline_nas_and_low_space(client,monkeypatch):
    browser,engine=client
    headers=signed_in(browser)
    payload={'confirmed':True,'files':[dlc_file()]}
    async def offline():return {'online':False,'writable':False,'free':0}
    monkeypatch.setattr(main,'storage',offline)
    assert browser.post('/api/downloads/dlc',headers=headers,json=payload).status_code==503
    async def full():return {'online':True,'writable':True,'free':100}
    monkeypatch.setattr(main,'storage',full)
    assert browser.post('/api/downloads/dlc',headers=headers,json=payload).status_code==507
    assert not engine.calls

def test_dlc_engine_failure_is_not_reported_as_success(client,monkeypatch):
    browser,engine=client
    async def unavailable(*args):return None
    monkeypatch.setattr(engine,'call',unavailable)
    response=browser.post('/api/downloads/dlc',headers=signed_in(browser),json={'confirmed':True,'files':[dlc_file()]})
    assert response.status_code==503
    with database.db() as connection:
        assert connection.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==0

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

def test_extension_token_is_required_and_links_reach_engine(client):
    browser,engine=client
    assert browser.post('/api/extension/status').status_code==401
    headers={'X-Extension-Token':'test-extension-token-1234567890x'}
    assert browser.post('/api/extension/status',headers=headers).status_code==200
    response=browser.post('/api/extension/links',headers=headers,json={'links':'https://example.org/from-extension.zip'})
    assert response.status_code==200
    assert engine.calls[0][0]=='/linkgrabberv2/addLinks'
    assert engine.calls[0][1][0]['links']=='https://example.org/from-extension.zip'
    assert 'test-extension-token' not in response.text

def test_extension_preflight_allows_browser_extensions_only(client):
    browser,_=client
    allowed={
        'Origin':'moz-extension://01234567-89ab-cdef-0123-456789abcdef',
        'Access-Control-Request-Method':'POST',
        'Access-Control-Request-Headers':'content-type,x-extension-token',
    }
    response=browser.options('/api/extension/status',headers=allowed)
    assert response.status_code==200
    assert response.headers['access-control-allow-origin']==allowed['Origin']
    response=browser.options('/api/extension/status',headers={**allowed,'Origin':'https://attacker.example'})
    assert response.status_code==400
    assert 'access-control-allow-origin' not in response.headers

def test_extension_token_can_only_be_read_by_signed_in_admin(client):
    browser,engine=client
    assert browser.get('/api/extension/token').status_code==401
    signed_in(browser)
    response=browser.get('/api/extension/token')
    assert response.status_code==200
    assert response.json()['token']=='test-extension-token-1234567890x'

def test_click_and_load_forwards_only_allowed_fields_to_loopback(client,monkeypatch):
    browser,engine=client
    captured={}
    class Response:
        def raise_for_status(self):pass
    class HttpClient:
        def __init__(self,*args,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,url,**kwargs):
            captured.update(url=url,**kwargs)
            return Response()
    monkeypatch.setattr(main.httpx,'AsyncClient',HttpClient)
    headers={'X-Extension-Token':'test-extension-token-1234567890x'}
    response=browser.post('/api/extension/cnl',headers=headers,json={'action':'add','fields':{'urls':'https://example.org/cnl.zip','source':'https://example.org/page','ignored':'private'}})
    assert response.status_code==200
    assert captured['url']=='http://127.0.0.1:9666/flash/add'
    assert b'urls=https%3A%2F%2Fexample.org%2Fcnl.zip' in captured['content']
    assert b'ignored' not in captured['content']
    assert 'X-Extension-Token' not in captured['headers']
    assert captured['headers']['Referer']=='http://127.0.0.1:9666/flashgot'
    assert browser.post('/api/extension/cnl',headers=headers,json={'action':'remove','fields':{'urls':'https://example.org'}}).status_code==422

def test_extraction_passwords_are_counted_but_never_returned_or_saved(client,monkeypatch):
    browser,engine=client
    headers=signed_in(browser)
    values=[]
    async def call(path,*params):
        engine.calls.append((path,params))
        if path=='/config/get':return list(values)
        if path=='/config/set':
            values[:]=params[-1]
            return True
        return True
    monkeypatch.setattr(engine,'call',call)
    secret='archive-test-secret-9247'
    response=browser.post('/api/settings/extraction/passwords',headers=headers,json={'password':secret})
    assert response.status_code==200
    assert response.json()['password_count']==1
    assert secret not in response.text
    response=browser.get('/api/settings/extraction')
    assert response.json()['password_count']==1
    assert secret not in response.text
    with database.db() as connection:
        assert secret not in '\n'.join(row[0] for row in connection.execute('SELECT value FROM settings'))
    response=browser.request('DELETE','/api/settings/extraction/passwords',headers=headers,json={'password':secret})
    assert response.status_code==200
    assert response.json()['password_count']==0
    assert not values
