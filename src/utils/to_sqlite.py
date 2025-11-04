"""
Conversion CSV nettoyés -> base SQLite utilisée par le dashboard.
Lit les fichiers de data/cleaned et crée les tables:
- caracteristiques, lieux, vehicules (import direct)
- usagers (schema propre: num_acc, catu, grav)
"""

import argparse
import sqlite3
import pandas as pd
from pathlib import Path
import re

INDEXES = {
    "caracteristiques": ["num_acc", "an", "mois", "dep"],
    "lieux": ["num_acc", "catr", "circ"],
    "vehicules": ["num_acc", "num_veh", "catv"],
    "usagers": ["num_acc", "catu", "grav", "an_nais"],
}

ALIASES = {
    "caracteristiques": "caracteristiques",
    "caract": "caracteristiques",
    "lieux": "lieux",
    "usagers": "usagers",
    "vehicules": "vehicules",
    "veh": "vehicules",
}

def guess_table_name(path: Path) -> str:
    stem = path.stem.lower()
    for k, v in ALIASES.items():
        if k in stem:
            return v
    name = re.sub(r"[^a-z0-9_]+", "_", stem)
    return re.sub(r"_+", "_", name).strip("_")

def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=OFF;")
    conn.execute("PRAGMA synchronous=OFF;")
    return conn

def _harmonize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    if "num_acc" not in df.columns:
        for c in df.columns:
            if c.replace("_", "").lower() == "numacc":
                df = df.rename(columns={c: "num_acc"})
                break
    return df

def import_table(conn, csv_path: Path, table: str):
    print(f"[+] Import de {csv_path.name} -> '{table}'")
    df = pd.read_csv(csv_path, sep=None, engine="python")
    df = _harmonize_cols(df)

    if table == "usagers":
        # on garde aussi an_nais pour les histogrammes d'âge
        keep = [x for x in ["num_acc", "catu", "grav", "an_nais"] if x in df.columns]
        df = df[keep].copy()

        # typage simple
        df["num_acc"] = pd.to_numeric(df.get("num_acc"), errors="coerce")
        df["catu"]    = pd.to_numeric(df.get("catu"),    errors="coerce")
        df["grav"]    = pd.to_numeric(df.get("grav"),    errors="coerce")
        df["an_nais"] = pd.to_numeric(df.get("an_nais"), errors="coerce")

        df = df.dropna(subset=["num_acc"]).astype({"num_acc": "int64"})
        # crée la table propre
        conn.execute("DROP TABLE IF EXISTS usagers;")
        conn.execute("""
            CREATE TABLE usagers (
                num_acc INTEGER NOT NULL,
                catu    INTEGER,
                grav    INTEGER,
                an_nais INTEGER
            );
        """)
        df.to_sql("usagers", conn, if_exists="append", index=False)
    else:
        # import direct pour les autres tables
        df.to_sql(table, conn, if_exists="replace", index=False)

    # index utiles
    for col in INDEXES.get(table, []):
        try:
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} ON {table}({col});")
        except Exception:
            pass


def main():
    p = argparse.ArgumentParser(description="CSV nettoyés -> SQLite (accidents)")
    p.add_argument("--input", nargs="+", required=True, help="Fichiers/dossiers CSV (ex: data/cleaned)")
    p.add_argument("--db", required=True, help="Chemin du .sqlite à créer")
    p.add_argument("--overwrite", action="store_true", help="Écrase la base existante")
    args = p.parse_args()

    db_path = Path(args.db)
    if db_path.exists() and args.overwrite:
        db_path.unlink()

    # liste des CSV
    csvs = []
    for item in args.input:
        pth = Path(item)
        if pth.is_dir():
            csvs += [f for f in pth.iterdir() if f.suffix.lower()==".csv"]
        elif pth.is_file() and pth.suffix.lower()==".csv":
            csvs.append(pth)
    if not csvs:
        raise FileNotFoundError("Aucun CSV trouvé dans --input")

    conn = connect_sqlite(db_path)
    try:
        for csv in csvs:
            table = guess_table_name(csv)
            import_table(conn, csv, table)
        conn.execute("ANALYZE;")
        conn.execute("VACUUM;")
        print(f"[OK] Base créée : {db_path}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
