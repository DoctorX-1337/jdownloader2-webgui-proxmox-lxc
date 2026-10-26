"""One NAS subfolder per native JDownloader package."""
import re
import unicodedata


def destination(root='/mnt/downloads'):
    return root.rstrip('/') + '/<jd:packagename>'


def folder_name(name, fallback='Downloadpaket'):
    value = unicodedata.normalize('NFC', str(name))
    value = re.sub(r'[\x00-\x1f/\\:*?"<>|]', '_', value).strip(' .')
    if not value:
        value = fallback
    if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', value):
        value = '_' + value
    while len(value.encode('utf-8')) > 220:
        value = value[:-1]
    return value
