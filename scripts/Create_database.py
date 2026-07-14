import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / 'data' / 'clinical_trials.db'
SCHEMA_PATH = PROJECT_ROOT / 'sql' / 'schema.sql'

def create_database():
    DB_PATH.parent.mkdir(exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f'Removed existing database: {DB_PATH}')

    conn = sqlite3.connect(DB_PATH)
    schema_sql = SCHEMA_PATH.read_text()
    conn.executescript(schema_sql)
    conn.commit()

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    conn.close()

    print(f'Database created: {DB_PATH}')
    print('Tables:', [t[0] for t in tables])

if __name__ == '__main__':
    create_database()

