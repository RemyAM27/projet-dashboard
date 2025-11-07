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

# Définition des index pour chaque table afin de faciliter les recherches dans la base
INDEXES = {
    "caracteristiques": ["num_acc", "an", "mois", "dep"],
    "lieux": ["num_acc", "catr", "circ"],
    "vehicules": ["num_acc", "num_veh", "catv"],
    "usagers": ["num_acc", "catu", "grav", "an_nais"],
}

# Alias permettant de trouver les tables dans les fichiers CSV
ALIASES = {
    "caracteristiques": "caracteristiques",
    "caract": "caracteristiques",
    "lieux": "lieux",
    "usagers": "usagers",
    "vehicules": "vehicules",
    "veh": "vehicules",
}

# Fonction pour deviner le nom de la table à partir du nom du fichier CSV
def guess_table_name(path: Path) -> str:
    """
    Lit le nom du fichier et le compare aux alias pour déterminer la table.
    Remplace les caractères non valides dans le nom du fichier pour créer un nom de table valide.
    """
    stem = path.stem.lower()
    for k, v in ALIASES.items():
        if k in stem:
            return v
    # Nettoyage du nom du fichier pour l'adapter à un format compatible avec SQLite
    name = re.sub(r"[^a-z0-9_]+", "_", stem)
    return re.sub(r"_+", "_", name).strip("_")

# Fonction pour se connecter à la base de données SQLite
def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    """
    Se connecte à la base SQLite et désactive les journaux et la synchronisation pour améliorer les performances.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=OFF;")  # Désactivation du journalisation
    conn.execute("PRAGMA synchronous=OFF;")  # Désactivation de la synchronisation pour plus de rapidité
    return conn

# Fonction pour harmoniser les colonnes des DataFrames afin qu'elles aient des noms cohérents
def _harmonize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Harmonise les noms des colonnes en les mettant en minuscules et en supprimant les espaces.
    Si la colonne "num_acc" n'existe pas, la recherche et la renomme si nécessaire.
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]  # Nettoyage des noms de colonnes
    if "num_acc" not in df.columns:
        for c in df.columns:
            if c.replace("_", "").lower() == "numacc":
                df = df.rename(columns={c: "num_acc"})  # Renommer la colonne si nécessaire
                break
    return df

# Fonction pour importer une table depuis un fichier CSV dans la base de données SQLite
def import_table(conn, csv_path: Path, table: str):
    """
    Importe un fichier CSV dans une table SQLite. Si la table est 'usagers', elle applique des règles spécifiques.
    """
    print(f"[+] Import de {csv_path.name} -> '{table}'")
    df = pd.read_csv(csv_path, sep=None, engine="python")  # Lecture du fichier CSV
    df = _harmonize_cols(df)  # Harmonisation des noms de colonnes

    if table == "usagers":
        # Si la table est 'usagers', on garde uniquement les colonnes nécessaires et les convertit en numériques
        keep = [x for x in ["num_acc", "catu", "grav", "an_nais"] if x in df.columns]
        df = df[keep].copy()

        df["num_acc"] = pd.to_numeric(df.get("num_acc"), errors="coerce")
        df["catu"]    = pd.to_numeric(df.get("catu"),    errors="coerce")
        df["grav"]    = pd.to_numeric(df.get("grav"),    errors="coerce")
        df["an_nais"] = pd.to_numeric(df.get("an_nais"), errors="coerce")

        df = df.dropna(subset=["num_acc"]).astype({"num_acc": "int64"})  # Supprimer les valeurs NaN et convertir en int

        # Supprimer la table existante et recréer la table 'usagers'
        conn.execute("DROP TABLE IF EXISTS usagers;")
        conn.execute("""
            CREATE TABLE usagers (
                num_acc INTEGER NOT NULL,
                catu    INTEGER,
                grav    INTEGER,
                an_nais INTEGER
            );
        """)
        df.to_sql("usagers", conn, if_exists="append", index=False)  # Insérer les données dans la table
    else:
        # Pour les autres tables, on insère les données directement
        df.to_sql(table, conn, if_exists="replace", index=False)

    # Créer les index pour améliorer les performances de recherche
    for col in INDEXES.get(table, []):
        try:
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_{col} ON {table}({col});")
        except Exception:
            pass

# Fonction principale qui gère le processus d'importation des fichiers CSV dans la base SQLite
def main():
    p = argparse.ArgumentParser(description="CSV nettoyés -> SQLite (accidents)")
    p.add_argument("--input", nargs="+", required=True, help="Fichiers/dossiers CSV (ex: data/cleaned)")
    p.add_argument("--db", required=True, help="Chemin du .sqlite à créer")
    p.add_argument("--overwrite", action="store_true", help="Écrase la base existante")
    args = p.parse_args()

    db_path = Path(args.db)
    if db_path.exists() and args.overwrite:
        db_path.unlink()  # Supprimer la base existante si l'option 'overwrite' est activée

    # Liste des fichiers CSV à importer
    csvs = []
    for item in args.input:
        pth = Path(item)
        if pth.is_dir():
            # Ajouter tous les fichiers CSV d'un dossier
            csvs += [f for f in pth.iterdir() if f.suffix.lower()==".csv"]
        elif pth.is_file() and pth.suffix.lower()==".csv":
            # Ajouter un fichier CSV spécifique
            csvs.append(pth)
    if not csvs:
        raise FileNotFoundError("Aucun CSV trouvé dans --input")

    # Connexion à la base de données SQLite
    conn = connect_sqlite(db_path)
    try:
        # Importer chaque fichier CSV dans la base de données
        for csv in csvs:
            table = guess_table_name(csv)  # Deviner le nom de la table à partir du fichier
            import_table(conn, csv, table)  # Importer les données dans la table correspondante
        conn.execute("ANALYZE;")  # Analyser la base de données après importation pour optimiser les performances
        conn.execute("VACUUM;")  # Compresser la base de données pour économiser de l'espace
        print(f"[OK] Base créée : {db_path}")
    finally:
        conn.close()  # Toujours fermer la connexion à la base de données

# Exécuter la fonction principale si ce script est lancé directement
if __name__ == "__main__":
    main()
