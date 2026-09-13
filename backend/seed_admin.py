"""One-time local provisioning using only a precomputed Argon2id hash."""
import json
import sys
from pathlib import Path
from app.database import db, initialize

initialize()
payload=json.loads(Path(sys.argv[1]).read_text())
assert payload['password_hash'].startswith('$argon2id$')
with db() as connection:
    if connection.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
        raise SystemExit('Administrator bereits eingerichtet; bestehendes Konto bleibt erhalten.')
    connection.execute('INSERT INTO users VALUES (?,?)',(payload['username'],payload['password_hash']))
print('Administrator eingerichtet. Setup ist abgeschlossen.')
