"""Read-only package summaries from JDownloader's native aggregate counters."""
from collections import defaultdict
from .extraction import for_package as package_extraction


def number(value):
    return max(0, value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def summarize(packages, links, controller):
    members = defaultdict(list)
    for link in links:
        members[str(link.get('packageUUID', ''))].append(link)
    native = {str(package['uuid']): package for package in packages}
    for ident, items in members.items():
        if ident not in native:
            native[ident] = {'uuid': ident, 'name': items[0].get('packageName') or 'Ohne Paketzuordnung'}
    result = []
    for ident, package in native.items():
        items = members.get(ident, [])
        if not items and not number(package.get('childCount')):
            continue
        # Native totals account for mirrors and include completed parts. Never
        # average per-file percentages or derive totals from active files only.
        total = number(package.get('bytesTotal')) if 'bytesTotal' in package else sum(number(x.get('bytesTotal')) for x in items)
        loaded = number(package.get('bytesLoaded')) if 'bytesLoaded' in package else sum(number(x.get('bytesLoaded')) for x in items)
        speed = number(package.get('speed')) if 'speed' in package else sum(number(x.get('speed')) for x in items)
        file_count = max(int(number(package.get('childCount'))), len(items))
        finished_count = sum(bool(x.get('finished')) for x in items)
        finished = bool(package.get('finished')) if 'finished' in package else bool(items) and finished_count == len(items)
        unknown = sum(not x.get('finished') and number(x.get('bytesTotal')) == 0 for x in items)
        extraction = package_extraction(items)
        extracting = bool(extraction and extraction['state'] == 'running') or any(x.get('extractionStatus') == 'RUNNING' for x in items)
        extraction_error = bool(extraction and extraction['state'] == 'error') or any(any(word in str(x.get('extractionStatus', '')).upper() for word in ('ERROR', 'FAILED')) for x in items)
        running = bool(package.get('running')) or speed > 0 or any(x.get('running') for x in items)
        paused = controller == 'PAUSE' or package.get('enabled') is False or bool(items) and all(x.get('enabled') is False for x in items)
        problems = sum(bool(x.get('skipped')) or 'error' in str(x.get('statusIconKey', '')).lower() for x in items)
        if extracting:
            status = 'extracting'
        elif extraction_error:
            status = 'extraction_error'
        elif finished:
            status = 'finished'
        elif paused:
            status = 'paused'
        elif running:
            status = 'running'
        elif problems:
            status = 'attention'
        else:
            status = 'queued'
        known = total > 0 and unknown == 0
        progress = 100.0 if finished else min(100.0, loaded / total * 100) if known else None
        remaining = number(package.get('eta'))
        if not remaining and known and speed > 0:
            remaining = max(0, total - loaded) / speed
        result.append({
            'uuid': ident, 'name': package.get('name') or 'Downloadpaket',
            'bytesLoaded': loaded, 'bytesTotal': total, 'progress': progress,
            'speed': speed if running and not paused else 0,
            'eta': int(remaining) if running and not paused and not finished else 0,
            'fileCount': file_count, 'finishedCount': file_count if finished else finished_count,
            'runningCount': sum(bool(x.get('running')) for x in items),
            'unknownSizeCount': unknown, 'problemCount': problems,
            'finished': finished, 'status': status, 'extraction': extraction,
        })
    return result
