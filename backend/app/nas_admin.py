import asyncio
import json
from pathlib import Path
from fastapi import HTTPException
from .config import NAS_ADMIN_HOST,NAS_ADMIN_KEY,NAS_ADMIN_KNOWN_HOSTS

async def rpc(payload):
    if not Path(NAS_ADMIN_KEY).is_file():
        raise HTTPException(503,'Die NAS-Verwaltung ist noch nicht eingerichtet. Bitte Proxmox-Anleitung prüfen.')
    args=['ssh','-T','-i',NAS_ADMIN_KEY,'-o','BatchMode=yes','-o','ConnectTimeout=10','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+NAS_ADMIN_KNOWN_HOSTS,'-o','IdentitiesOnly=yes','jd2mount@'+NAS_ADMIN_HOST]
    process=await asyncio.create_subprocess_exec(*args,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.DEVNULL)
    try:
        output,_=await asyncio.wait_for(process.communicate(json.dumps(payload).encode()),timeout=85)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise HTTPException(503,'NAS-Prüfung dauert zu lange. Bitte den Status neu laden.') from None
    try:
        result=json.loads(output)
    except ValueError:
        raise HTTPException(503,'Die Verbindung zur NAS-Verwaltung ist fehlgeschlagen.') from None
    if process.returncode or result.get('success') is False:
        raise HTTPException(422,result.get('detail','NAS-Einstellung konnte nicht übernommen werden.'))
    return result
