"""Read-only extraction telemetry from JDownloader's native PluginProgress."""


def positive(value):
    return max(0, value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def from_link(link, advanced):
    advanced = advanced if isinstance(advanced, dict) else {}
    progress = advanced.get('PluginProgress') or {}
    native = (advanced.get('ExtractionStatus') or {}).get('id') or link.get('extractionStatus')
    extracting = progress.get('id') == 'EXTRACTION'
    if not native and not extracting:
        return None
    if extracting or native == 'RUNNING':
        state = 'running'
    elif native == 'SUCCESSFUL':
        state = 'finished'
    elif any(word in str(native) for word in ('ERROR', 'ERRROR', 'FAILED')):
        state = 'error'
    else:
        state = 'queued'
    current = positive(progress.get('current')) if extracting else 0
    total = positive(progress.get('total')) if extracting else 0
    percent = 100.0 if state == 'finished' else min(100.0, current / total * 100) if total else None
    label = ''.join(char for char in str(progress.get('label') or '') if ord(char) >= 32)[:512] if extracting else ''
    defaults = {'running':'Archiv wird entpackt', 'finished':'Entpacken abgeschlossen', 'queued':'Wartet auf Entpacken', 'error':'Entpacken fehlgeschlagen'}
    if not label or label.lower().startswith(('extracting', 'entpacken', 'entpacke')):
        label = defaults[state]
    errors = {'ERROR_PW':'Entpackpasswort erforderlich', 'ERROR_CRC':'Prüfsummenfehler beim Entpacken', 'ERROR_NOT_ENOUGH_SPACE':'Nicht genügend Speicherplatz zum Entpacken', 'ERRROR_FILE_NOT_FOUND':'Ein Archivteil fehlt'}
    if state == 'error':
        label = errors.get(native, defaults[state])
    return {'state':state, 'progress':percent, 'bytesProcessed':current, 'bytesTotal':total,
            'eta':int(positive(progress.get('eta')) / 1000) if extracting else 0,
            'label':label}


def for_package(links):
    items = [link['extraction'] for link in links if isinstance(link.get('extraction'), dict)]
    if not items:
        return None
    # One archive reports the same controller counters on every RAR part.
    # Show one native archive's progress instead of adding those counters or
    # averaging unrelated archives in the package.
    for state in ('running', 'error', 'queued'):
        candidates = [item for item in items if item.get('state') == state]
        if candidates:
            return dict(next((item for item in candidates if item.get('progress') is not None), candidates[0]))
    return dict(items[0])
