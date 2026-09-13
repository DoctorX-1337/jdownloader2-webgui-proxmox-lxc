import asyncio
import json
import os
import signal
import sys
from .config import NAS_CHECK, NAS_SOURCE

OFFLINE = {'online': False, 'writable': False, 'free':0, 'total':0}

async def storage():
    env = dict(os.environ, NAS_SOURCE=NAS_SOURCE)
    try:
        process = await asyncio.create_subprocess_exec('timeout','--kill-after=1','10',sys.executable,NAS_CHECK, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, env=env, start_new_session=True)
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout=12)
        except asyncio.TimeoutError:
            os.killpg(process.pid, signal.SIGKILL)
            return dict(OFFLINE)
        if process.returncode:
            return dict(OFFLINE)
        return json.loads(output)
    except (OSError, ValueError):
        return dict(OFFLINE)
