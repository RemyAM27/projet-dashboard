"""
Ce script convertit les fichiers CSV des accidents corporels
en une base SQLite. Il peut traiter un ou plusieurs fichiers,
ou un dossier complet contenant les CSV.
"""

import argparse
import sqlite3
import pandas as pd
from pathlib import Path
import re

# Lecture par morceaux (gros fichiers)
CHUNK_SIZE = 200_000

# Correspondance nom de fichier -> table
ALIASES = {
    "caracteristiques": "caracteristiques",
    "caract": "caracteristiques",
    "lieux": "lieux",
    "usagers": "usagers",
    "vehicules": "vehicules",
    "veh": "vehicules",
}

# Index utiles pour le dashboard
INDEXES = {
    "caracteristiques": ["Num_Acc", "an", "mois", "dep"],
    "lieux": ["Num_Acc", "catr", "circ"],
    "vehicules": ["Num_Acc", "num_veh", "catv"],
    "usagers": ["Num_Acc", "num_veh", "grav"],
}

def guess_table_name(path: Path) -> str:
    """Nom de table à partir du nom de fichier."""
    stem = path.stem.lower()
    for k, v in ALIASES.items():
        if k in stem:
            return v
    name = re.sub(r"[^a-z0-9_]+", "_", stem)
    return re.sub(r"_+", "_", name).strip("_")

def list_csv(inputs):
    """Liste des CSV à traiter."""
    paths = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            paths += sorted([f for f in p.iterdir() if f.suffix.lower() == ".csv"])
        elif p.is_file() and p.suffix.lower() == ".csv":
            paths.append(p)
    if not paths:
        raise FileNotFoundError("Aucun fichier CSV trouvé.")
    return paths

def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    """Connexion SQLite (quelques réglages pour l'import)."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=OFF;")
    conn.execute("PRAGMA synchronous=OFF;")
    return conn

def ensure_table(conn, table, columns):
    """Crée la table si absente (colonnes TEXT pour robustesse)."""
    cols_sql = ", ".join(f'"{c}" TEXT' for c in columns)
    conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({cols_sql});')

def _append_chunk(conn, table: str, chunk: pd.DataFrame):
    """Insertion robuste : sous-batches pour éviter 'too many SQL variables'."""
    ncols = max(1, len(chunk.columns))
    # Limite SQLite ~999 variables → marge 900
    max_rows = max(1, 900 // ncols)
    chunk.to_sql(
        table, conn,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=max_rows
    )

def import_csv(conn, csv_path: Path, table: str):
    """Lit le CSV en chunks et insère dans SQLite.
    Teste plusieurs séparateurs; en dernier recours, saute les lignes invalides.
    """
    attempts = [
        {"sep": ";", "engine": "python"},
        {"sep": ",", "engine": "python"},
        {"sep": None, "engine": "python"},  # détection auto
        {"sep": "\t", "engine": "python"},
    ]

    first_chunk = True
    for opts in attempts:
        try:
            reader = pd.read_csv(
                csv_path,
                dtype=str,
                chunksize=CHUNK_SIZE,
                encoding_errors="ignore",
                **opts
            )
            for chunk in reader:
                chunk.columns = [str(c).strip() for c in chunk.columns]
                if first_chunk:
                    ensure_table(conn, table, list(chunk.columns))
                    first_chunk = False
                _append_chunk(conn, table, chunk)
            print(f"    → OK avec sep={opts['sep'] if opts['sep'] is not None else 'auto'}")
            return
        except Exception:
            # on essaie l'option suivante
            continue

    # Dernier recours : ignorer uniquement les lignes mal formées
    print("    ! Lignes mal formées détectées, on les saute (on_bad_lines='skip').")
    reader = pd.read_csv(
        csv_path,
        dtype=str,
        chunksize=CHUNK_SIZE,
        engine="python",
        sep=None,                # auto
        on_bad_lines="skip",     # pandas >= 1.4
        encoding_errors="ignore",
    )
    first_chunk = True
    for chunk in reader:
        chunk.columns = [str(c).strip() for c in chunk.columns]
        if first_chunk:
            ensure_table(conn, table, list(chunk.columns))
            first_chunk = False
        _append_chunk(conn, table, chunk)

def create_indexes(conn, table: str):
    """Index simples pour accélérer les recherches."""
    for col in INDEXES.get(table, []):
        try:
            conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table}_{col} ON {table}({col});')
        except sqlite3.Error:
            pass

def main():
    parser = argparse.ArgumentParser(description="Conversion CSV -> SQLite (accidents)")
    parser.add_argument("--input", nargs="+", required=True,
                        help="Chemin(s) des fichiers ou dossier contenant les CSV.")
    parser.add_argument("--db", required=True, help="Chemin du fichier .sqlite à créer.")
    parser.add_argument("--overwrite", action="store_true", help="Écrase la base existante.")
    args = parser.parse_args()

    db_path = Path(args.db)
    if db_path.exists() and args.overwrite:
        db_path.unlink()

    conn = connect_sqlite(db_path)
    csv_files = list_csv(args.input)

    try:
        for csv in csv_files:
            table = guess_table_name(csv)
            print(f"[+] Import de {csv.name} → table '{table}'")
            import_csv(conn, csv, table)
            create_indexes(conn, table)
        conn.execute("ANALYZE;")
        conn.execute("VACUUM;")
        print(f"[OK] Base créée : {db_path}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
