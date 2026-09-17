"""Authentication shared only with the local browser extension."""
import hmac
import secrets
from fastapi import Header, HTTPException
from .config import EXTENSION_TOKEN_FILE

def token():
    try:
        value = EXTENSION_TOKEN_FILE.read_text(encoding='ascii').strip()
    except OSError:
        raise HTTPException(503, 'Browser-Erweiterung ist noch nicht eingerichtet.') from None
    if len(value) < 32:
        raise HTTPException(503, 'Browser-Erweiterung ist noch nicht eingerichtet.')
    return value

def require(x_extension_token: str = Header(default='')):
    if not hmac.compare_digest(x_extension_token, token()):
        raise HTTPException(401, 'Browser-Erweiterung ist nicht autorisiert.')
    return True

def rotate():
    value = secrets.token_urlsafe(36)
    with EXTENSION_TOKEN_FILE.open('w', encoding='ascii') as file:
        file.write(value+'\n')
    EXTENSION_TOKEN_FILE.chmod(0o600)
    return value
