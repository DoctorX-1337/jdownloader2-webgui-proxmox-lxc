#!/usr/bin/env python3
"""Restricted Proxmox-side NAS RPC. No shell commands from input, no secret output."""
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time

CT='200'
BASE=Path('/etc/jdownloader-nas')
MOUNT=Path('/mnt/nas-server-jdownloader')
CANDIDATE=Path('/mnt/jdownloader-nas-candidate')
STATE=BASE/'state.json'
CREDENTIALS=BASE/'credentials'

def run(args,timeout=45):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout)
    if result.returncode:raise RuntimeError('Systemaktion fehlgeschlagen')
    return result.stdout.strip()

def save(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False))
    temporary.chmod(0o600)
    temporary.replace(path)

def state():
    return json.loads(STATE.read_text()) if STATE.exists() else {'target':r'\\NAS-SERVER\media\Downloads','status':'ready','message':'NAS verbunden.'}

def parse_target(value):
    value=value.strip().replace('\\','/')
    if not value.startswith('//'):raise ValueError('Bitte einen NAS-Pfad wie \\\\NAS-SERVER\\media\\Downloads eingeben.')
    parts=value[2:].rstrip('/').split('/')
    if len(parts)<2 or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.\-]{0,252}',parts[0]):raise ValueError('NAS-Hostname oder Freigabe ist ungültig.')
    for part in parts[1:]:
        if not part or part in ('.','..') or any(ord(c)<32 or c in ':*?"<>|,' for c in part) or len(part)>255:
            raise ValueError('NAS-Pfad enthält ungültige Zeichen.')
    if len(value)>1024:raise ValueError('NAS-Pfad ist zu lang.')
    host=parts[0]
    # Use the known NAS IP to keep boot independent of local DNS.
    if host.lower() in ('nas-server','nas-server.fritz.box'):host='192.0.2.30'
    return '//'+host+'/'+parts[1],parts[2:],'\\\\'+'\\'.join(parts)

def options(credential,version):
    return f'credentials={credential},vers={version},uid=101000,gid=101000,forceuid,forcegid,file_mode=0660,dir_mode=0770,nosuid,nodev,noexec,_netdev'

def safe_directory(root,parts):
    path=root
    for part in parts:
        path=path/part
        if path.is_symlink():raise ValueError('Symbolische NAS-Pfade sind nicht zulässig.')
        if not path.exists():path.mkdir()
        if not path.is_dir():raise ValueError('Der NAS-Zielpfad ist kein Verzeichnis.')
    if not path.resolve().is_relative_to(root.resolve()):raise ValueError('Der NAS-Zielpfad verlässt die Freigabe.')
    return path

def configure(payload):
    current=state()
    if current.get('status')=='pending':raise ValueError('Ein NAS-Wechsel läuft bereits. Bitte warten.')
    source,parts,target=parse_target(payload.get('target',''))
    username=payload.get('username','')
    password=payload.get('password','')
    if any(c in username+password for c in '\r\n\x00'):raise ValueError('Ungültige NAS-Zugangsdaten.')
    pending=BASE/('pending-'+secrets.token_hex(8)+'.json')
    credential=pending.with_suffix('.credentials')
    if username:
        if not password:raise ValueError('Bitte das NAS-Passwort zur neuen Anmeldung angeben.')
        credential.write_text('username='+username+'\npassword='+password+'\n')
    else:
        credential.write_bytes(CREDENTIALS.read_bytes())
    credential.chmod(0o600)
    CANDIDATE.mkdir(mode=0o000,exist_ok=True)
    mounted=False
    try:
        for version in ('3.1.1','3.0','2.1','2.0'):
            try:
                run(['mount','-t','cifs',source,str(CANDIDATE),'-o',options(credential,version)],timeout=12)
                mounted=True
                break
            except (RuntimeError,subprocess.TimeoutExpired):pass
        if not mounted:raise ValueError('NAS-Freigabe nicht erreichbar oder Anmeldung fehlgeschlagen. Das bisherige Ziel bleibt erhalten.')
        destination=safe_directory(CANDIDATE,parts)
        probe='import tempfile,os,sys; f=tempfile.TemporaryFile(dir=sys.argv[1]); f.write(b"jd2-target-check"); f.flush(); os.fsync(f.fileno()); f.close()'
        run(['setpriv','--reuid=101000','--regid=101000','--clear-groups','python3','-c',probe,str(destination)],timeout=12)
        run(['umount',str(CANDIDATE)])
        mounted=False
        job={'source':source,'parts':parts,'target':target,'version':version,'credential':str(credential),'previous_state':current}
        save(pending,job)
        save(STATE,{'target':current['target'],'pendingTarget':target,'status':'pending','message':'Neues NAS geprüft. Container wird kurz neu gestartet.'})
        run(['systemd-run','--quiet','--unit=jd2-nas-apply-'+secrets.token_hex(4),'--on-active=5s','/usr/bin/python3',__file__,'apply',str(pending)])
        return {'success':True,'restarting':True,'target':target,'message':'NAS-Ziel geprüft. Der Container startet kurz neu; die Seite verbindet sich automatisch wieder.'}
    except Exception:
        if mounted:
            try:run(['umount',str(CANDIDATE)])
            except Exception:pass
        credential.unlink(missing_ok=True)
        pending.unlink(missing_ok=True)
        if state().get('status')=='pending':save(STATE,current)
        raise

def change_container_env(source,parts):
    run(['pct','mount',CT])
    try:
        path=Path('/var/lib/lxc')/CT/'rootfs/etc/jdownloader-web/config.env'
        previous=path.read_text()
        values={'NAS_SOURCE':source,'NAS_ROOT':'/'+'/'.join(parts),'NAS_TARGET':r'\\'+source[2:].replace('/','\\')+('\\'+'\\'.join(parts) if parts else '')}
        lines=[line for line in previous.splitlines() if line.split('=',1)[0] not in values]
        # Shell-compatible quoting for dotenv + systemd EnvironmentFile.
        for key,value in values.items():lines.append(key+'='+json.dumps(value,ensure_ascii=False))
        path.write_text('\n'.join(lines)+'\n')
        return previous
    finally:run(['pct','unmount',CT])

def restore_env(text):
    run(['pct','mount',CT])
    try:(Path('/var/lib/lxc')/CT/'rootfs/etc/jdownloader-web/config.env').write_text(text)
    finally:run(['pct','unmount',CT])

def apply(pending):
    job=json.loads(pending.read_text())
    fstab=Path('/etc/fstab')
    previous_fstab=fstab.read_text()
    previous_credential=CREDENTIALS.read_bytes()
    config=run(['pct','config',CT])
    previous_mp=next(x.split(': ',1)[1] for x in config.splitlines() if x.startswith('mp0:'))
    previous_env=None
    try:
        run(['pct','shutdown',CT,'--timeout','30'],timeout=40)
        run(['umount',str(MOUNT)])
        CREDENTIALS.write_bytes(Path(job['credential']).read_bytes())
        CREDENTIALS.chmod(0o600)
        source_fstab=job['source'].replace('\\',r'\134').replace(' ',r'\040').replace('\t',r'\011')
        line=source_fstab+' '+str(MOUNT)+' cifs '+options(CREDENTIALS,job['version'])+',x-systemd.mount-timeout=20s 0 0'
        lines=[x for x in previous_fstab.splitlines() if len(x.split())<2 or x.split()[1]!=str(MOUNT)]
        fstab.write_text('\n'.join(lines+[line])+'\n')
        run(['systemctl','daemon-reload'])
        run(['mount',str(MOUNT)])
        destination=safe_directory(MOUNT,job['parts'])
        # pct's volume syntax uses commas as separators; commas are rejected.
        run(['pct','set',CT,'--mp0',str(destination)+',mp=/mnt/downloads,backup=0'])
        previous_env=change_container_env(job['source'],job['parts'])
        run(['pct','start',CT],timeout=60)
        save(STATE,{'target':job['target'],'status':'ready','message':'NAS-Ziel übernommen.','updated':time.time()})
    except Exception:
        try:
            status=run(['pct','status',CT])
            if 'running' in status:run(['pct','shutdown',CT,'--timeout','30'],timeout=40)
            subprocess.run(['umount',str(MOUNT)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
            CREDENTIALS.write_bytes(previous_credential)
            CREDENTIALS.chmod(0o600)
            fstab.write_text(previous_fstab)
            run(['systemctl','daemon-reload'])
            run(['mount',str(MOUNT)])
            run(['pct','set',CT,'--mp0',previous_mp])
            if previous_env is not None:restore_env(previous_env)
            run(['pct','start',CT],timeout=60)
            save(STATE,{'target':job['previous_state']['target'],'status':'error','message':'NAS-Wechsel fehlgeschlagen. Bisheriges Ziel wurde wiederhergestellt.'})
        except Exception:
            save(STATE,{'target':job['previous_state']['target'],'status':'error','message':'NAS-Wechsel fehlgeschlagen. Bitte Proxmox-Konsole prüfen; Downloads bleiben blockiert.'})
    finally:
        Path(job['credential']).unlink(missing_ok=True)
        pending.unlink(missing_ok=True)

def main():
    BASE.mkdir(mode=0o700,exist_ok=True)
    if len(sys.argv)==3 and sys.argv[1]=='apply':
        path=Path(sys.argv[2]).resolve()
        if path.parent!=BASE or not path.name.startswith('pending-'):raise ValueError('Ungültiger Auftrag')
        apply(path)
        return
    raw=sys.stdin.buffer.read(65537)
    if len(raw)>65536:raise ValueError('Anfrage zu groß')
    payload=json.loads(raw)
    if payload.get('action')=='status':print(json.dumps(state(),ensure_ascii=False));return
    if payload.get('action')!='configure':raise ValueError('Aktion nicht verfügbar')
    with (BASE/'lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        print(json.dumps(configure(payload),ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except ValueError as error:print(json.dumps({'success':False,'detail':str(error)},ensure_ascii=False))
    except Exception:print(json.dumps({'success':False,'detail':'NAS-Konfiguration fehlgeschlagen. Das bisherige Ziel bleibt erhalten.'},ensure_ascii=False))
