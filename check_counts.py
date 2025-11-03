import sqlite3
from pathlib import Path

db = Path("data/accidents.sqlite")
conn = sqlite3.connect(db)

for table in ["caracteristiques", "lieux", "vehicules", "usagers"]:
    try:
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {n:,} lignes")
    except Exception as e:
        print(f"{table}: erreur ({e})")

conn.close()
