#!/usr/bin/env python3
"""Create deterministic Chromium and Firefox packages from shared sources."""
from pathlib import Path
import json
import shutil
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'browser-extension'
PUBLIC=ROOT/'frontend/public'
FILES=['background.js','options.html','options.js','options.css']
ICONS={16:'favicon-16x16.png',32:'favicon-32x32.png',192:'android-chrome-192x192.png'}
for browser in ('chromium','firefox'):
    manifest=json.loads((SOURCE/f'manifest.{browser}.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as folder:
        work=Path(folder)
        (work/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        for name in FILES:shutil.copy2(SOURCE/name,work/name)
        (work/'icons').mkdir()
        for size,name in ICONS.items():shutil.copy2(PUBLIC/name,work/'icons'/f'icon-{size}.png')
        output=PUBLIC/f'jdownloader2-{browser}-extension.zip'
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for file in sorted(work.rglob('*')):
                if not file.is_file():continue
                info=zipfile.ZipInfo(file.relative_to(work).as_posix(),(2026,1,1,0,0,0));info.external_attr=0o100644<<16
                archive.writestr(info,file.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        with zipfile.ZipFile(output) as archive:
            assert archive.testzip() is None
signed=SOURCE/'signed'/'jdownloader2-firefox-extension.xpi'
installable=PUBLIC/'jdownloader2-firefox-extension.xpi'
if signed.exists():
    with zipfile.ZipFile(signed) as archive:
        assert archive.testzip() is None
        manifest=json.loads(archive.read('manifest.json'))
        assert manifest['browser_specific_settings']['gecko']['id']=='jdownloader2-local@custom.local'
    shutil.copy2(signed,installable)
elif installable.exists():
    installable.unlink()
print('Browser-Erweiterungen für Chromium und Firefox erstellt.')
