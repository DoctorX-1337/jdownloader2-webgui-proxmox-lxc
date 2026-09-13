#!/usr/bin/env python3
"""Write a bootstrap hash without echoing or storing the entered password."""
import getpass
import json
import os
import sys
from argon2 import PasswordHasher

password=getpass.getpass('Neues Administrator-Passwort: ')
if len(password)<12: raise SystemExit('Mindestens 12 Zeichen verwenden.')
if password!=getpass.getpass('Passwort bestätigen: '): raise SystemExit('Passwörter stimmen nicht überein.')
path=sys.argv[1] if len(sys.argv)>1 else '/tmp/jdownloader-admin.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o640)
with os.fdopen(fd,'w') as file: json.dump({'username':'admin','password_hash':PasswordHasher().hash(password)},file)
print('Bootstrap-Datei geschrieben; sie enthält ausschließlich den Passwort-Hash.')
