#!/usr/bin/env python3
"""Opt-in migration of idle package folders using JDownloader's native mover.

Default: read-only plan. --apply moves complete packages and adjusts unstarted
ones. Running/partially downloaded packages and active extractions are skipped.
An on-disk journal records every output rename; ambiguous files stay in place.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.download_folders import folder_name

ROOT = Path('/mnt/downloads')


def call(endpoint, *params):
    request = urllib.request.Request('http://127.0.0.1:3128'+endpoint,
                                     data=json.dumps({'params':list(params)}).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if 'type' in result:
        raise RuntimeError('Native API-Aktion nicht bestätigt.')
    return result.get('data')


def snapshot():
    packages = call('/downloadsV2/queryPackages', dict(startAt=0,maxResults=-1,saveTo=True,finished=True,running=True,bytesLoaded=True))
    links = call('/downloadsV2/queryLinks', dict(startAt=0,maxResults=-1,finished=True,running=True,bytesLoaded=True,bytesTotal=True,extractionStatus=True))
    queue = call('/extraction/getQueue')
    busy_names = {name for archive in queue for name in (archive.get('states') or {})}
    busy = {str(l.get('packageUUID')) for l in links if l.get('name') in busy_names or l.get('running') or l.get('extractionStatus') == 'RUNNING'}
    return packages, links, busy


def archive_members(path):
    """Read headers only. Encrypted/unsupported headers remain unclassified."""
    binary = '/usr/bin/7zz' if Path('/usr/bin/7zz').exists() else '/usr/bin/7z'
    try:
        result = subprocess.run([binary,'l','-slt','--',str(path)],stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,timeout=30)
    except (OSError,subprocess.TimeoutExpired):
        return {}
    if result.returncode or '----------' not in result.stdout:
        return {}
    records = result.stdout.split('----------',1)[1].strip().split('\n\n')
    members = {}
    for block in records:
        row = dict(line.split(' = ',1) for line in block.splitlines() if ' = ' in line)
        name = row.get('Path','').replace('\\','/')
        rel = PurePosixPath(name)
        if not name or rel.is_absolute() or '..' in rel.parts or any(':' in p for p in rel.parts) or row.get('Folder') == '+':
            continue
        if row.get('Symbolic Link') or row.get('Hard Link'):
            continue
        if row.get('Size','').isdigit():
            members[str(rel)] = int(row['Size'])
    return members


def safe_file(path):
    return path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)) and path.resolve().is_relative_to(ROOT.resolve())


def plan():
    packages, links, busy = snapshot()
    extracting = bool(call('/extraction/getQueue'))
    owners = Counter(l['name'] for l in links)
    targets = Counter(folder_name(p['name']) for p in packages)
    rows = []
    for p in packages:
        group = [l for l in links if l.get('packageUUID') == p['uuid']]
        ident = str(p['uuid'])
        if p.get('saveTo') != str(ROOT) or ident in busy or p.get('running') or targets[folder_name(p['name'])] != 1:
            continue
        finished = bool(p.get('finished')) and group and all(l.get('finished') for l in group)
        unstarted = group and all(not l.get('bytesLoaded') and not l.get('finished') for l in group)
        if not finished and not unstarted:
            continue
        target = ROOT / folder_name(p['name'])
        if target.exists() or target.is_symlink() or any(owners[l['name']] != 1 or Path(l['name']).name != l['name'] for l in group):
            continue
        if unstarted and any((ROOT/(l['name']+'.part')).exists() or (ROOT/l['name']).exists() for l in group):
            continue
        outputs = {}
        archive_files = {l['name']: (ROOT/l['name']).stat().st_size for l in group if safe_file(ROOT/l['name'])}
        if finished and not extracting:
            for name in archive_files:
                part = re.search(r'(?i)\.part(\d+)\.rar$', name)
                first = int(part[1]) == 1 if part else bool(re.search(r'(?i)\.(?:rar|zip|7z)(?:\.001)?$',name))
                if first:
                    outputs.update(archive_members(ROOT/name))
        rows.append(dict(id=ident,target=str(target),finished=finished,links=[str(l['uuid']) for l in group],files=archive_files,outputs=outputs))
    output_owners = Counter(name for row in rows for name in row['outputs'])
    for row in rows:
        row['outputs'] = {name:size for name,size in row['outputs'].items() if output_owners[name] == 1 and name not in owners and safe_file(ROOT/name) and (ROOT/name).stat().st_size == size}
    return rows


def apply(rows, journal):
    counts = Counter()
    for row in rows:
        packages, links, busy = snapshot()
        p = next((p for p in packages if str(p['uuid']) == row['id']), None)
        group = [l for l in links if str(l.get('packageUUID')) == row['id']]
        target = Path(row['target'])
        if not p or p.get('saveTo') != str(ROOT) or row['id'] in busy or p.get('running') or target.exists() or {str(l['uuid']) for l in group} != set(row['links']):
            counts['skipped_changed'] += 1
            continue
        if row['finished'] and (not p.get('finished') or not all(l.get('finished') for l in group)):
            counts['skipped_changed'] += 1
            continue
        if not row['finished'] and any(l.get('bytesLoaded') or l.get('finished') for l in group):
            counts['skipped_changed'] += 1
            continue
        if any(not safe_file(ROOT/name) or (ROOT/name).stat().st_size != size for name,size in row['files'].items()):
            counts['skipped_changed'] += 1
            continue
        journal['actions'].append(dict(package=row['id'],target=str(target),stage='requested',renames=[]))
        journal_path.write_text(json.dumps(journal))
        call('/downloadsV2/setDownloadDirectory', str(target), [int(row['id'])])
        for attempt in range(30):
            updated = call('/downloadsV2/queryPackages', dict(startAt=0,maxResults=-1,saveTo=True))
            if any(str(p['uuid']) == row['id'] and p.get('saveTo') == str(target) for p in updated) and all(safe_file(target/name) and (target/name).stat().st_size == size and not (ROOT/name).exists() for name,size in row['files'].items()):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError('Paketverschiebung noch nicht vollständig bestätigt. Journal prüfen; keine weiteren Pakete geändert.')
        journal['actions'][-1]['stage'] = 'native-moved'
        journal_path.write_text(json.dumps(journal))
        counts['finished_packages' if row['finished'] else 'unstarted_packages'] += 1
        counts['archive_files'] += len(row['files'])
        for name,size in row['outputs'].items():
            if call('/extraction/getQueue'):
                counts['outputs_skipped'] += 1
                continue
            source = ROOT/name
            destination = target/name
            if not safe_file(source) or source.stat().st_size != size or destination.exists() or destination.is_symlink():
                counts['outputs_skipped'] += 1
                continue
            destination.parent.mkdir(parents=True,exist_ok=True)
            if any(p.is_symlink() for p in (destination.parent, *destination.parent.parents)):
                raise RuntimeError('Symbolischer Zielpfad erkannt.')
            # renameat2 RENAME_NOREPLACE avoids overwriting a concurrent output.
            import ctypes
            libc = ctypes.CDLL(None,use_errno=True)
            rc = libc.renameat2(-100,os.fsencode(source),-100,os.fsencode(destination),1)
            if rc:
                counts['outputs_skipped'] += 1
                continue
            journal['actions'][-1]['renames'].append([str(source),str(destination)])
            journal_path.write_text(json.dumps(journal))
            counts['extracted_files'] += 1
        journal['actions'][-1]['stage'] = 'complete'
        journal_path.write_text(json.dumps(journal))
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true')
    args = parser.parse_args()
    if not os.path.ismount(ROOT):
        raise SystemExit('NAS-Bind-Mount fehlt; Abbruch.')
    rows = plan()
    print(json.dumps({'planned_packages':len(rows),'completed':sum(r['finished'] for r in rows),'unstarted':sum(not r['finished'] for r in rows),'archive_files':sum(len(r['files']) for r in rows),'extracted_files':sum(len(r['outputs']) for r in rows)}))
    if args.apply:
        directory = Path('/var/lib/jdownloader-web/folder-migrations')
        directory.mkdir(mode=0o700,exist_ok=True)
        journal_path = directory / (time.strftime('%Y%m%d-%H%M%S')+'.json')
        fd = os.open(journal_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        os.close(fd)
        journal = {'plan':rows,'actions':[]}
        print(json.dumps(apply(rows,journal)))
