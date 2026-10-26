#!/usr/bin/env python3
"""Remember controller intent across an NAS guard stop, without resetting links."""
import json
import os
from pathlib import Path
import sys
import urllib.request

LAST = Path('/run/jdownloader-controller-state')
BLOCKED = Path('/run/jdownloader-nas-blocked')


def call(endpoint, *args):
    request = urllib.request.Request('http://127.0.0.1:' + str(int(os.getenv('JD_PORT','3128'))) + endpoint,
                                     data=json.dumps({'params':list(args)}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=2) as response:
        body = json.load(response)
    if 'type' in body:
        raise RuntimeError('Lokale Engine noch nicht bereit.')
    return body.get('data')


def read(path):
    return path.read_text().strip() if path.exists() else ''


def write(path, state):
    temporary = path.with_suffix('.new')
    fd = os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as handle:
        handle.write(state)
    temporary.replace(path)


def remember():
    try:
        state = call('/downloadcontroller/getCurrentState')
        if state == 'STOPPING':
            state = 'IDLE'
        if state in ('RUNNING','PAUSE','PAUSED','IDLE','STOPPED'):
            write(LAST,state)
    except Exception:
        pass


def block():
    if not BLOCKED.exists():
        remember()
        write(BLOCKED,read(LAST) or 'IDLE')


def recover():
    if read(BLOCKED) != 'RUNNING':
        return True
    try:
        state = call('/downloadcontroller/getCurrentState')
        if state in ('IDLE','STOPPED'):
            call('/downloadcontroller/start')
            state = call('/downloadcontroller/getCurrentState')
        # A deliberate current pause takes precedence over the earlier state.
        return state in ('RUNNING','PAUSE','PAUSED')
    except Exception:
        return False


if __name__ == '__main__':
    if sys.argv[1] == 'remember': remember()
    elif sys.argv[1] == 'block': block()
    elif sys.argv[1] == 'recover': sys.exit(0 if recover() else 1)
    else: sys.exit(2)
