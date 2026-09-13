import sqlite3
from contextlib import contextmanager
from .config import DATA, DATABASE

@contextmanager
def db():
    connection = sqlite3.connect(DATABASE, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()

def initialize():
    DATA.mkdir(parents=True, exist_ok=True)
    with db() as connection:
        connection.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, csrf TEXT NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts (ip TEXT NOT NULL, created REAL NOT NULL);
        CREATE INDEX IF NOT EXISTS attempts_created ON attempts(created);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS history (uuid TEXT PRIMARY KEY, name TEXT NOT NULL, host TEXT, size INTEGER, finished REAL);
        CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, submitted INTEGER NOT NULL, created REAL NOT NULL);
        ''')
