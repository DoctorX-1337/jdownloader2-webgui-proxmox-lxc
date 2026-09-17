import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.getenv('APP_CONFIG', '/etc/jdownloader-web/config.env'))
DATA = Path(os.getenv('APP_DATA', '/var/lib/jdownloader-web'))
DATABASE = DATA / 'app.db'
DOWNLOAD_PATH = '/mnt/downloads'
NAS_SOURCE = os.getenv('NAS_SOURCE', '//192.0.2.30/media')
NAS_ROOT = os.getenv('NAS_ROOT','/Downloads')
NAS_TARGET = os.getenv('NAS_TARGET',r'\\NAS-SERVER\media\Downloads')
NAS_ADMIN_HOST = os.getenv('NAS_ADMIN_HOST','192.0.2.10')
NAS_ADMIN_KEY = os.getenv('NAS_ADMIN_KEY','/etc/jdownloader-web/nas_key')
NAS_ADMIN_KNOWN_HOSTS = os.getenv('NAS_ADMIN_KNOWN_HOSTS','/etc/jdownloader-web/nas_known_hosts')
SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '86400'))
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
NAS_CHECK = os.getenv('NAS_CHECK', '/usr/local/lib/jdownloader/check-nas.py')
EXTENSION_TOKEN_FILE = Path(os.getenv('EXTENSION_TOKEN_FILE', '/etc/jdownloader-web/browser-extension.token'))
CNL_PORT = int(os.getenv('CNL_PORT', '9666'))
