from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3


class Database:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        self.path = directory / "course.sqlite3"
        with self.connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute('CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY)')
            current = conn.execute('SELECT COALESCE(MAX(version),0) FROM schema_version').fetchone()[0]
            for migration in sorted((Path(__file__).parent / "migrations").glob("*.sql")):
                version=int(migration.name.split('_')[0])
                if version > current:
                    conn.executescript(migration.read_text())
                    conn.execute('INSERT OR IGNORE INTO schema_version VALUES (?)',(version,))
        self.path.chmod(0o600)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, sql, values=()):
        with self.connection() as conn:
            return conn.execute(sql, values).rowcount

    def all(self, sql, values=()):
        with self.connection() as conn:
            return [dict(row) for row in conn.execute(sql, values).fetchall()]

    def one(self, sql, values=()):
        rows = self.all(sql, values)
        return rows[0] if rows else None

    def setting(self, key, default=None):
        row = self.one("SELECT value FROM settings WHERE key=?", (key,))
        return json.loads(row["value"]) if row else default

    def save_setting(self, key, value):
        self.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))

