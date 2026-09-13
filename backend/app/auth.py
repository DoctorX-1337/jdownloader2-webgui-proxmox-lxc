import hashlib
import hmac
import logging
import secrets
import time
from urllib.parse import urlsplit
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import HTTPException, Request, Response
from .config import COOKIE_SECURE, SESSION_TIMEOUT
from .database import db

hasher = PasswordHasher()
dummy_hash = hasher.hash(secrets.token_urlsafe(32))
logger = logging.getLogger('jdweb')

def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def check_origin(request: Request):
    origin = request.headers.get('origin')
    if origin:
        source = urlsplit(origin)
        if source.scheme != request.url.scheme or source.netloc != request.url.netloc:
            raise HTTPException(403, 'Diese Anfrage ist nicht erlaubt.')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'Diese Anfrage ist nicht erlaubt.')

def session(request: Request):
    token = request.cookies.get('jd_session', '')
    with db() as connection:
        row = connection.execute('SELECT * FROM sessions WHERE token_hash=? AND expires>?', (digest(token), time.time())).fetchone()
    if not row:
        raise HTTPException(401, 'Bitte anmelden.')
    if request.method not in ('GET','HEAD','OPTIONS'):
        check_origin(request)
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), row['csrf']):
            raise HTTPException(403, 'Sitzung bitte neu laden und erneut versuchen.')
    return dict(row)

def login(request: Request, response: Response, username: str, password: str, remember: bool):
    check_origin(request)
    now = time.time()
    ip = request.client.host if request.client else 'unknown'
    with db() as connection:
        connection.execute('DELETE FROM attempts WHERE created<?', (now-900,))
        connection.execute('DELETE FROM sessions WHERE expires<?', (now,))
        count = connection.execute('SELECT COUNT(*) FROM attempts WHERE ip=?', (ip,)).fetchone()[0]
        if count >= 5:
            raise HTTPException(429, 'Zu viele Anmeldeversuche. Bitte in 15 Minuten erneut versuchen.', headers={'Retry-After':'900'})
        row = connection.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        try:
            valid = hasher.verify(row['password_hash'] if row else dummy_hash, password)
        except (VerificationError, InvalidHashError):
            valid = False
        if not row or not valid:
            connection.execute('INSERT INTO attempts VALUES (?,?)', (ip, now))
            connection.commit()
            logger.info('Login fehlgeschlagen')
            raise HTTPException(401, 'Benutzername oder Passwort ist falsch.')
        connection.execute('DELETE FROM attempts WHERE ip=?', (ip,))
        previous = request.cookies.get('jd_session', '')
        connection.execute('DELETE FROM sessions WHERE token_hash=?', (digest(previous),))
        token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        lifetime = SESSION_TIMEOUT * (30 if remember else 1)
        connection.execute('INSERT INTO sessions VALUES (?,?,?,?)', (digest(token), username, csrf, now+lifetime))
        if hasher.check_needs_rehash(row['password_hash']):
            connection.execute('UPDATE users SET password_hash=? WHERE username=?', (hasher.hash(password), username))
    response.set_cookie('jd_session', token, httponly=True, secure=COOKIE_SECURE, samesite='strict', max_age=lifetime if remember else None, path='/')
    logger.info('Login erfolgreich')
    return {'username':username, 'csrf':csrf}
