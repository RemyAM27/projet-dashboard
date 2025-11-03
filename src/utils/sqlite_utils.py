from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, Iterable, Tuple
import pandas as pd

# ------------------------------------------------------------
# Connexion SQLite robuste
# ------------------------------------------------------------
def connect(db_path: Path) -> sqlite3.Connection:
    """Connexion SQLite en lecture seule, compatible Windows."""
    p = Path(db_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"Base SQLite introuvable : {p}")
    uri = f"file:{p.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ------------------------------------------------------------
# Outils internes : lister et résoudre les tables
# ------------------------------------------------------------
def _list_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """)
    return [r[0] for r in cur.fetchall()]


def _resolve_table_names(conn: sqlite3.Connection) -> tuple[str, str]:
    """
    Tente de trouver les tables équivalentes à 'caracteristiques' et 'lieux'
    même si elles ont des variantes de nom.
    """
    names = _list_tables(conn)
    lower = {n.lower(): n for n in names}

    cand_carac = ["caracteristiques", "caract", "caracteristique"]
    cand_lieux = ["lieux", "lieu"]

    def pick(cands):
        for c in cands:
            if c in lower:
                return lower[c]
        for n in names:
            ln = n.lower()
            for c in cands:
                if ln.startswith(c):
                    return n
        return None

    t_carac = pick(cand_carac)
    t_lieux = pick(cand_lieux)

    if not t_carac or not t_lieux:
        raise RuntimeError(
            f"Impossible de trouver les tables 'caracteristiques'/'lieux'. "
            f"Tables disponibles : {names}"
        )
    return t_carac, t_lieux


# ------------------------------------------------------------
# Lecture simple d'une table
# ------------------------------------------------------------
def read_table(
    db_path: Path,
    table: str,
    columns: Optional[Iterable[str]] = None,
    where: Optional[str] = None,
    params: Optional[Tuple[Any, ...] | Dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:
    cols = ", ".join(columns) if columns else "*"
    q = f"SELECT {cols} FROM {table}"
    if where:
        q += f" WHERE {where}"
    if limit:
        q += f" LIMIT {int(limit)}"
    with connect(db_path) as conn:
        return pd.read_sql(q, conn, params=params)


# ------------------------------------------------------------
# Lecture combinée caractéristiques + lieux (robuste)
# ------------------------------------------------------------
def load_join_carac_lieux(db_path: Path, year: Optional[int] = None) -> pd.DataFrame:
    """Charge les données en aliasant dynamiquement les colonnes vers des noms standard.
       Joint 'lieux' uniquement si la colonne 'catr' existe EXACTEMENT et si on connaît la clé accident côté 'lieux'.
    """
    def _list_cols(conn, table: str) -> list[str]:
        rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        return [r[1] for r in rows]

    def pick_exact(colnames: list[str], target: str) -> Optional[str]:
        for name in colnames:
            if name.lower() == target.lower():
                return name
        return None

    def pick_any(colnames: list[str], candidates: list[str]) -> Optional[str]:
        # match exact insensible à la casse sur l'une des candidatures
        lowset = {c.lower() for c in colnames}
        for cand in candidates:
            if cand.lower() in lowset:
                # renvoie le nom avec sa casse originale
                for n in colnames:
                    if n.lower() == cand.lower():
                        return n
        return None

    with connect(db_path) as conn:
        t_carac, t_lieux = _resolve_table_names(conn)
        carac_cols = _list_cols(conn, t_carac)
        lieux_cols = _list_cols(conn, t_lieux)

        # Colonnes côté caracteristiques
        acc_carac  = pick_any(carac_cols, ["num_acc", "Num_Acc", "numacc", "num_accident", "accident"])
        year_col   = pick_any(carac_cols, ["an", "annee", "année", "year"])
        mois_col   = pick_any(carac_cols, ["mois", "month"])
        dep_col    = pick_any(carac_cols, ["dep", "departement", "département", "code_dep", "dep_code"])
        hrmn_col   = pick_any(carac_cols, ["hrmn", "heure", "time"])
        lat_col    = pick_any(carac_cols, ["lat", "latitude"])
        lon_col    = pick_any(carac_cols, ["long", "lon", "longitude"])

        # Colonnes indispensables min
        required = {"Num_Acc": acc_carac, "an": year_col, "mois": mois_col, "dep": dep_col}
        missing = [k for k, v in required.items() if v is None]
        if missing:
            raise RuntimeError(
                "Colonnes indispensables introuvables dans 'caracteristiques'. "
                f"Manquantes (alias attendus): {missing}\n"
                f"Colonnes disponibles: {carac_cols}"
            )

        # Côté lieux : on ne retient que des matches **EXACTS**
        acc_lieux = pick_any(lieux_cols, ["num_acc", "Num_Acc"])
        catr_col  = pick_exact(lieux_cols, "catr")  # EXACTEMENT 'catr'

        join_lieux = (acc_lieux is not None) and (catr_col is not None)

        # Filtre année
        where = []
        params: Dict[str, Any] = {}
        if year is not None and year_col is not None:
            where.append(f'c."{year_col}" = :year')
            params["year"] = int(year)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        # SELECT standardisé
        select_parts = [
            f'c."{acc_carac}"  AS "Num_Acc"',
            f'c."{year_col}"   AS "an"',
            f'c."{mois_col}"   AS "mois"',
            f'c."{dep_col}"    AS "dep"',
        ]
        if hrmn_col: select_parts.append(f'c."{hrmn_col}" AS "hrmn"')
        if lat_col:  select_parts.append(f'c."{lat_col}"  AS "lat"')
        if lon_col:  select_parts.append(f'c."{lon_col}"  AS "long"')

        if join_lieux:
            select_sql = ", ".join(select_parts + [f'l."{catr_col}" AS "catr"'])
            q = f'''
                SELECT {select_sql}
                FROM "{t_carac}" c
                LEFT JOIN "{t_lieux}" l ON l."{acc_lieux}" = c."{acc_carac}"
                {where_sql}
            '''
        else:
            # Pas de colonne 'catr' EXACTE -> pas de jointure
            select_sql = ", ".join(select_parts)
            q = f'''
                SELECT {select_sql}
                FROM "{t_carac}" c
                {where_sql}
            '''

        return pd.read_sql(q, conn, params=params or None)

