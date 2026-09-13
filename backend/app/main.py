import asyncio
from contextlib import asynccontextmanager, suppress
import json
import logging
import re
import socket
import time
from urllib.parse import urlsplit
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, SecretStr
from . import auth, config
from .database import db, initialize
from .jd import JDownloader, EngineUnavailable
from .storage import storage, OFFLINE

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger('jdweb')
jd = JDownloader()
current = {'nas':dict(OFFLINE), 'jdownloader':False, 'internet':False, 'version':None, 'updated':0}

def setting(key, default):
    with db() as connection:
        row = connection.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    return json.loads(row['value']) if row else default

async def network_available():
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection('installer.jdownloader.org',443), timeout=3)
        writer.close()
        await writer.wait_closed()
        return True
    except (OSError, asyncio.TimeoutError):
        return False

async def monitor():
    while True:
        try:
            nas, internet = await asyncio.gather(storage(), network_available())
            try:
                version = await jd.call('/jd/version')
                online = True
                links = await jd.downloads()
                with db() as connection:
                    for link in links:
                        if link.get('finished'):
                            finished = link.get('finishedDate',0) / 1000 or time.time()
                            connection.execute('INSERT OR IGNORE INTO history VALUES (?,?,?,?,?)', (link['uuid'],link['name'],link.get('host',''),link.get('bytesTotal',link.get('bytesLoaded',0)),finished))
            except EngineUnavailable:
                online, version = False, None
            for label, old, new in [('NAS',current['nas']['online'],nas['online']),('JDownloader',current['jdownloader'],online)]:
                if old != new:
                    logger.info('%s %s', label, 'online' if new else 'offline')
            current.update(nas=nas, internet=internet, jdownloader=online, version=version, updated=time.time())
        except Exception:
            current.update(nas=dict(OFFLINE), jdownloader=False, updated=time.time())
            logger.error('Systemüberwachung fehlgeschlagen')
        await asyncio.sleep(5)

@asynccontextmanager
async def lifespan(app):
    initialize()
    task = asyncio.create_task(monitor())
    logger.info('Anwendung gestartet')
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    await jd.client.aclose()

app = FastAPI(title='JDownloader Custom WebUI', docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

@app.exception_handler(EngineUnavailable)
async def engine_error(request, error):
    logger.warning('JDownloader API nicht erreichbar')
    return JSONResponse(status_code=503, content={'detail':'JDownloader ist momentan nicht erreichbar. Es wurde kein Erfolg bestätigt.'})

@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    # Validation errors must never echo password input.
    return JSONResponse(status_code=422, content={'detail':'Bitte die Eingaben prüfen.'})

@app.exception_handler(Exception)
async def internal_error(request, error):
    logger.error('Interner Anwendungsfehler: %s',type(error).__name__)
    return JSONResponse(status_code=500, content={'detail':'Die Anfrage konnte nicht verarbeitet werden. Bitte erneut versuchen.'})

class Login(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(max_length=256)
    remember: bool = False

@app.post('/api/auth/login')
def login(body:Login, request:Request, response:Response):
    return auth.login(request,response,body.username,body.password.get_secret_value(),body.remember)

@app.get('/api/auth/session')
def get_session(user=Depends(auth.session)):
    return {'username':user['username'],'csrf':user['csrf']}

@app.post('/api/auth/logout')
def logout(response:Response, user=Depends(auth.session)):
    with db() as connection:
        connection.execute('DELETE FROM sessions WHERE token_hash=?', (user['token_hash'],))
    response.delete_cookie('jd_session', path='/')
    return {'success':True}

class ChangePassword(BaseModel):
    old_password: SecretStr = Field(max_length=256)
    new_password: SecretStr = Field(min_length=12, max_length=256)

@app.post('/api/auth/password')
def change_password(body:ChangePassword, response:Response, user=Depends(auth.session)):
    from argon2.exceptions import VerificationError
    with db() as connection:
        row = connection.execute('SELECT password_hash FROM users WHERE username=?', (user['username'],)).fetchone()
        try:
            auth.hasher.verify(row['password_hash'], body.old_password.get_secret_value())
        except VerificationError:
            raise HTTPException(403, 'Das aktuelle Passwort ist falsch.') from None
        connection.execute('UPDATE users SET password_hash=? WHERE username=?',(auth.hasher.hash(body.new_password.get_secret_value()),user['username']))
        connection.execute('DELETE FROM sessions')
    response.delete_cookie('jd_session', path='/')
    return {'success':True}

@app.get('/api/health')
def health():
    fresh = time.time()-current['updated'] < 30
    return {'application':'online','jdownloader':'online' if current['jdownloader'] and fresh else 'offline','nas':'online' if current['nas']['online'] and fresh else 'offline','nasWritable':current['nas']['writable'] and fresh}

@app.get('/api/system/status')
def status(user=Depends(auth.session)):
    fresh = time.time()-current['updated'] < 30
    return dict(current, nas=current['nas'] if fresh else dict(OFFLINE), jdownloader=current['jdownloader'] and fresh, downloadPath=config.DOWNLOAD_PATH, nasPath=config.NAS_TARGET, hostname=socket.gethostname())

@app.get('/api/system/storage')
async def get_storage(user=Depends(auth.session)):
    return await storage()

async def require_nas():
    nas = await storage()
    if not nas['online'] or not nas['writable']:
        raise HTTPException(503, 'NAS nicht verfügbar – Downloads wurden deaktiviert.')
    if nas['free'] < 256*1024*1024:
        raise HTTPException(507, 'Auf dem NAS steht nicht genügend freier Speicherplatz zur Verfügung.')

def parse_links(value):
    raw = re.split(r'\s+',value.strip()) if isinstance(value,str) else value
    unique=[]
    for link in raw:
        if not link:
            continue
        parsed=urlsplit(link)
        if parsed.scheme not in ('http','https','ftp') or not parsed.hostname or parsed.username or parsed.password or len(link)>4096:
            raise HTTPException(422, 'Bitte gültige HTTP-, HTTPS- oder FTP-Links ohne Zugangsdaten eingeben.')
        if any(ord(c)<32 for c in link):
            raise HTTPException(422,'Ein Link enthält ungültige Zeichen.')
        if link not in unique:
            unique.append(link)
    if not unique or len(unique)>100:
        raise HTTPException(422, 'Bitte zwischen 1 und 100 Links eingeben.')
    return unique

class NewDownload(BaseModel):
    links: str | list[str]

@app.post('/api/downloads')
async def add_download(body:NewDownload, user=Depends(auth.session)):
    links = parse_links(body.links)
    await require_nas()
    job = await jd.call('/linkgrabberv2/addLinks', {'links':'\n'.join(links),'destinationFolder':config.DOWNLOAD_PATH,'autostart':setting('autostart',True),'autoExtract':setting('auto_extract',True),'assignJobID':True,'overwritePackagizerRules':True})
    if not isinstance(job,dict) or 'id' not in job:
        raise EngineUnavailable()
    with db() as connection:
        connection.execute('INSERT OR REPLACE INTO jobs VALUES (?,?,?)',(str(job['id']),len(links),time.time()))
    logger.info('Downloadauftrag erstellt: %d Links',len(links))
    return {'success':True,'submitted':len(links),'job':str(job['id']),'message':f'{len(links)} Links werden analysiert. JDownloader verarbeitet sie automatisch.'}

@app.get('/api/downloads')
async def downloads(user=Depends(auth.session)):
    links, packages, state = await asyncio.gather(jd.downloads(),jd.call('/downloadsV2/queryPackages',{'startAt':0,'maxResults':-1}),jd.call('/downloadcontroller/getCurrentState'))
    names={str(p['uuid']):p['name'] for p in packages}
    for link in links:
        link['packageName']=names.get(link['packageUUID'],'')
    return {'links':links,'state':state,'speed':sum(x.get('speed',0) for x in links)}

@app.get('/api/downloads/active')
async def active(user=Depends(auth.session)):
    return [link for link in await jd.downloads() if not link.get('finished')]

@app.get('/api/downloads/history')
def history(user=Depends(auth.session)):
    with db() as connection:
        return [dict(row) for row in connection.execute('SELECT * FROM history ORDER BY finished DESC LIMIT 100')]

@app.get('/api/linkgrabber')
async def grabber(user=Depends(auth.session)):
    return {'links':await jd.grabber(),'collecting':await jd.call('/linkgrabberv2/isCollecting')}

def link_id(value):
    if not value.isdecimal() or int(value)<=0 or int(value)>2**63-1:
        raise HTTPException(422,'Ungültige Download-ID.')
    return int(value)

@app.post('/api/downloads/{id}/{action}')
async def action(id:str, action:str, user=Depends(auth.session)):
    ident=link_id(id)
    if action=='pause':
        await jd.call('/downloadsV2/setEnabled',False,[ident],[])
    elif action in ('resume','retry'):
        await require_nas()
        if action=='retry':
            await jd.call('/downloadsV2/resetLinks',[ident],[])
        else:
            await jd.call('/downloadsV2/resumeLinks',[ident],[])
        await jd.call('/downloadsV2/setEnabled',True,[ident],[])
        await jd.call('/downloadcontroller/pause',False)
        await jd.call('/downloadcontroller/start')
    else:
        raise HTTPException(404,'Aktion nicht verfügbar.')
    return {'success':True}

@app.delete('/api/downloads/{id}')
async def remove(id:str,user=Depends(auth.session)):
    await jd.call('/downloadsV2/removeLinks',[link_id(id)],[])
    return {'success':True}

@app.post('/api/linkgrabber/{id}/start')
async def start_grabbed(id:str,user=Depends(auth.session)):
    ident=link_id(id)
    await require_nas()
    links=await jd.grabber()
    link=next((x for x in links if x['uuid']==id),None)
    if not link:
        raise HTTPException(404,'Link nicht gefunden.')
    if link.get('availability')=='OFFLINE':
        raise HTTPException(422,'Dieser Link ist beim Anbieter nicht verfügbar.')
    await jd.call('/linkgrabberv2/setDownloadDirectory',config.DOWNLOAD_PATH,[int(link['packageUUID'])])
    await jd.call('/linkgrabberv2/moveToDownloadlist',[ident],[])
    await jd.call('/downloadcontroller/pause',False)
    await jd.call('/downloadcontroller/start')
    return {'success':True}

@app.delete('/api/linkgrabber/{id}')
async def remove_grabbed(id:str,user=Depends(auth.session)):
    await jd.call('/linkgrabberv2/removeLinks',[link_id(id)],[])
    return {'success':True}

@app.post('/api/controller/{action}')
async def controller(action:str,user=Depends(auth.session)):
    if action=='start':
        await require_nas()
        await jd.call('/downloadcontroller/pause',False)
        await jd.call('/downloadcontroller/start')
    elif action=='pause':
        await jd.call('/downloadcontroller/pause',True)
    elif action=='stop':
        await jd.call('/downloadcontroller/stop')
    else:
        raise HTTPException(404,'Aktion nicht verfügbar.')
    return {'success':True}

class Settings(BaseModel):
    parallel: int = Field(ge=1,le=20)
    chunks: int = Field(ge=1,le=20)
    speed_limit: int = Field(ge=0,le=1000000)
    autostart: bool
    auto_extract: bool

@app.get('/api/settings')
async def get_settings(user=Depends(auth.session)):
    interface='org.jdownloader.settings.GeneralSettings'
    values=await asyncio.gather(*(jd.call('/config/get',interface,None,key) for key in ['MaxSimultaneDownloads','MaxChunksPerFile','DownloadSpeedLimit','DownloadSpeedLimitEnabled']))
    return {'parallel':values[0],'chunks':values[1],'speed_limit':round(values[2]/1024) if values[3] else 0,'autostart':setting('autostart',True),'auto_extract':setting('auto_extract',True)}

@app.put('/api/settings')
async def save_settings(body:Settings,user=Depends(auth.session)):
    interface='org.jdownloader.settings.GeneralSettings'
    values=[('MaxSimultaneDownloads',body.parallel),('MaxChunksPerFile',body.chunks),('DownloadSpeedLimitEnabled',body.speed_limit>0)]
    if body.speed_limit>0:
        values.insert(2,('DownloadSpeedLimit',body.speed_limit*1024))
    for key,value in values:
        if not await jd.call('/config/set',interface,None,key,value):
            raise HTTPException(503,'JDownloader konnte eine Einstellung nicht übernehmen. Bitte neu laden.')
    with db() as connection:
        for key,value in [('autostart',body.autostart),('auto_extract',body.auto_extract)]:
            connection.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(key,json.dumps(value)))
    return {'success':True}

@app.get('/api/jobs')
def jobs(user=Depends(auth.session)):
    with db() as connection:
        return [dict(row) for row in connection.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 50')]

class NasSettings(BaseModel):
    target: str = Field(min_length=5,max_length=1024)
    username: str = Field(default='',max_length=256)
    password: SecretStr = Field(default=SecretStr(''),max_length=256)

@app.get('/api/settings/nas')
async def nas_settings(user=Depends(auth.session)):
    from .nas_admin import rpc
    return await rpc({'action':'status'})

@app.put('/api/settings/nas')
async def save_nas(body:NasSettings,user=Depends(auth.session)):
    from .nas_admin import rpc
    return await rpc({'action':'configure','target':body.target,'username':body.username,'password':body.password.get_secret_value()})

@app.get('/api/accounts/hosts')
async def premium_hosts(user=Depends(auth.session)):
    hosts=await jd.call('/accountsV2/listPremiumHosterUrls')
    return sorted(hosts.keys())

@app.get('/api/accounts')
async def accounts(user=Depends(auth.session)):
    rows=await jd.call('/accountsV2/listAccounts',{'startAt':0,'maxResults':-1,'userName':True,'enabled':True,'valid':True,'trafficLeft':True,'trafficMax':True,'validUntil':True})
    allowed=('hostname','username','enabled','valid','trafficLeft','trafficMax','validUntil','errorType')
    return [dict({k:row[k] for k in allowed if k in row},uuid=str(row['uuid'])) for row in rows]

class PremiumAccount(BaseModel):
    host: str = Field(min_length=1,max_length=253)
    username: str = Field(min_length=1,max_length=256)
    password: SecretStr = Field(min_length=1,max_length=256)

@app.post('/api/accounts')
async def add_account(body:PremiumAccount,user=Depends(auth.session)):
    hosts=await jd.call('/accountsV2/listPremiumHosterUrls')
    host=body.host.strip().lower()
    if host not in hosts:
        raise HTTPException(422,'Dieser Anbieter wird von JDownladers Accountverwaltung nicht unterstützt. Bitte einen Anbieter aus der Liste wählen.')
    await jd.call('/accountsV2/addAccount',host,body.username,body.password.get_secret_value())
    rows=await jd.call('/accountsV2/listAccounts',{'startAt':0,'maxResults':-1,'userName':True})
    if not any(row.get('hostname','').lower()==host and row.get('username')==body.username for row in rows):
        raise HTTPException(503,'Der Account wurde von JDownloader nicht bestätigt. Bitte Anbieter und Zugangsdaten prüfen.')
    logger.info('Premium-Account an JDownloader übergeben')
    return {'success':True,'message':'Account an JDownloader übergeben. Die Zugangsdaten werden jetzt beim Anbieter geprüft.'}

class AccountEnabled(BaseModel):
    enabled: bool

@app.put('/api/accounts/{id}')
async def account_enabled(id:str,body:AccountEnabled,user=Depends(auth.session)):
    await jd.call('/accountsV2/enableAccounts' if body.enabled else '/accountsV2/disableAccounts',[link_id(id)])
    return {'success':True}

@app.post('/api/accounts/{id}/refresh')
async def refresh_account(id:str,user=Depends(auth.session)):
    await jd.call('/accountsV2/refreshAccounts',[link_id(id)],True)
    return {'success':True}

@app.delete('/api/accounts/{id}')
async def remove_account(id:str,user=Depends(auth.session)):
    await jd.call('/accountsV2/removeAccounts',[link_id(id)])
    return {'success':True}
