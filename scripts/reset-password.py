#!/usr/bin/env python3
import getpass
from app.auth import hasher
from app.database import db

password=getpass.getpass('Neues Administrator-Passwort: ')
if len(password)<12: raise SystemExit('Mindestens 12 Zeichen verwenden.')
if password!=getpass.getpass('Bestätigen: '): raise SystemExit('Passwörter stimmen nicht überein.')
with db() as connection:
 connection.execute('UPDATE users SET password_hash=? WHERE username=?',(hasher.hash(password),'admin'))
 connection.execute('DELETE FROM sessions')
print('Passwort geändert; alle Sitzungen abgemeldet.')
