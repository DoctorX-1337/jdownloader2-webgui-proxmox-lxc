#!/usr/bin/env python3
"""Run under an external timeout: CIFS operations may block in the kernel."""
import json
import os
import re
from pathlib import Path
import tempfile

def check():
    path = Path(os.getenv('DOWNLOAD_PATH','/mnt/downloads'))
    mounts = Path('/proc/self/mountinfo').read_text().splitlines()
    found = False
    for line in mounts:
        before, after = line.split(' - ', 1)
        unescape = lambda value: re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1], 8)), value)
        fields = [unescape(value) for value in before.split()]
        fs = [unescape(value) for value in after.split()]
        if fields[4] == path.as_posix() and fs[0] == 'cifs' and fs[1] == os.getenv('NAS_SOURCE','//192.0.2.30/media'):
            found = fields[3] == os.getenv('NAS_ROOT','/Downloads')
    if not found:
        raise OSError('NAS mount fehlt')
    with tempfile.TemporaryFile(dir=path) as probe:
        probe.write(b'jd2-healthcheck')
        probe.flush()
        os.fsync(probe.fileno())
    st = os.statvfs(path)
    return {'online': True, 'writable': True, 'free': st.f_bavail * st.f_frsize, 'total': st.f_blocks * st.f_frsize}

if __name__ == '__main__':
    try:
        print(json.dumps(check()))
    except OSError:
        print(json.dumps({'online': False, 'writable': False, 'free': 0, 'total': 0}))
        raise SystemExit(1)
