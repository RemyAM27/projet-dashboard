# clean_data.py
# Script de nettoyage léger des CSV 2024 -> CSV nettoyés dans data/cleaned/
# Usage :  python clean_data.py

from __future__ import annotations
from pathlib import Path
import pandas as pd

RAW = Path("data/raw")
CLEAN = Path("data/cleaned")

FILES = {
    "caract": RAW / "Caract_2024.csv",
    "lieux": RAW / "Lieux_2024.csv",
    "vehicules": RAW / "Vehicules_2024.csv",
    "usagers": RAW / "Usagers_2024.csv",
}

def _read_csv_any(path: Path) -> pd.DataFrame:
    """Lecture simple : tente d'abord sep=';' (fréquent sur data.gouv), sinon ','."""
    try:
        return pd.read_csv(path, sep=";", low_memory=False)
    except Exception:
        return pd.read_csv(path, sep=",", low_memory=False)

def _std_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise basiquement les colonnes :
    - noms en minuscules
    - enlève espaces autour des noms
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def _norm_num_acc(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise la clé num_acc si présente : string, trim."""
    df = df.copy()
    for k in ("num_acc", "numacc", "num-acc"):
        if k in df.columns:
            df["num_acc"] = df[k].astype(str).str.strip()
            if k != "num_acc":
                df = df.drop(columns=[k])
            break
    return df

def _clean_caract(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoyage léger des caractéristiques :
    - normalise num_acc
    - pad département (dep) sur 2 caractères si numérique
    - construit une date approximative si colonnes (an, mois, jour) présentes
    """
    df = _std_cols(df)
    df = _norm_num_acc(df)

    # DEP (ex : 1 -> '01', 2A/2B laissés tels quels si déjà string)
    if "dep" in df.columns:
        # on ne touche pas aux '2A/2B' déjà strings
        df["dep"] = df["dep"].astype(str).str.strip()
        df.loc[df["dep"].str.fullmatch(r"\d+"), "dep"] = (
            df.loc[df["dep"].str.fullmatch(r"\d+"), "dep"].str.zfill(2)
        )

    # Date (si an/mois/jour existent)
    if all(col in df.columns for col in ("an", "mois", "jour")):
        df["an"] = pd.to_numeric(df["an"], errors="coerce")
        df["mois"] = pd.to_numeric(df["mois"], errors="coerce")
        df["jour"] = pd.to_numeric(df["jour"], errors="coerce")
        df["date"] = pd.to_datetime(
            dict(year=df["an"].fillna(2024).astype(int),
                 month=df["mois"].fillna(1).astype(int).clip(1, 12),
                 day=df["jour"].fillna(1).astype(int).clip(1, 31)),
            errors="coerce"
        )

    # Heure (si 'hrmn' existe, format HHMM)
    if "hrmn" in df.columns:
        s = df["hrmn"].astype(str).str.strip().str.zfill(4)
        hh = pd.to_numeric(s.str.slice(0, 2), errors="coerce").clip(0, 23)
        mm = pd.to_numeric(s.str.slice(2, 4), errors="coerce").clip(0, 59)
        df["heure"] = (hh.fillna(0).astype(int).astype(str).str.zfill(2)
                       + ":" +
                       mm.fillna(0).astype(int).astype(str).str.zfill(2))

    return df

def _clean_lieux(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyage léger des lieux : standardisation colonnes + num_acc."""
    df = _std_cols(df)
    df = _norm_num_acc(df)
    return df

def _clean_vehicules(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyage léger des véhicules : standardisation colonnes + num_acc si présent."""
    df = _std_cols(df)
    df = _norm_num_acc(df)
    # assurer présence d'un identifiant véhicule si existe avec noms variables
    for cand in ("num_veh", "id_veh", "numveh"):
        if cand in df.columns:
            df["id_veh"] = df[cand].astype(str).str.strip()
            if cand != "id_veh":
                df = df.drop(columns=[cand])
            break
    return df

def _clean_usagers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoyage léger des usagers :
    - standardisation colonnes
    - num_acc normalisé
    - calcul âge (si an_nais présent), borné 0..110
    - libellé gravité (si 'grav' présente)
    """
    df = _std_cols(df)
    df = _norm_num_acc(df)

    if "an_nais" in df.columns:
        an_nais = pd.to_numeric(df["an_nais"], errors="coerce")
        df["age"] = (2024 - an_nais).clip(lower=0, upper=110)

    if "grav" in df.columns:
        # codes usuels : 1 Indemne, 2 Tué, 3 Blessé hospitalisé, 4 Blessé léger
        mapping = {1: "Indemne", 2: "Tué", 3: "Hospitalisé", 4: "Léger"}
        df["grav_label"] = pd.to_numeric(df["grav"], errors="coerce").map(mapping)

    # harmonise l'id véhicule si relié à la table véhicules
    for cand in ("id_veh", "num_veh", "numveh"):
        if cand in df.columns:
            df["id_veh"] = df[cand].astype(str).str.strip()
            break

    return df

def _write_clean(df: pd.DataFrame, name_out: str) -> None:
    CLEAN.mkdir(parents=True, exist_ok=True)
    out = CLEAN / name_out
    df.to_csv(out, index=False)
    print(f"✔ {out} ({len(df):,} lignes)")

def main() -> None:
    # CARACT
    if not FILES["caract"].exists():
        raise FileNotFoundError(f"Fichier manquant : {FILES['caract']} (lance d'abord get_data.py)")
    df_car = _clean_caract(_read_csv_any(FILES["caract"]))
    _write_clean(df_car, "Caract_2024_clean.csv")

    # LIEUX
    if not FILES["lieux"].exists():
        raise FileNotFoundError(f"Fichier manquant : {FILES['lieux']}")
    df_lieux = _clean_lieux(_read_csv_any(FILES["lieux"]))
    _write_clean(df_lieux, "Lieux_2024_clean.csv")

    # VEHICULES
    if not FILES["vehicules"].exists():
        raise FileNotFoundError(f"Fichier manquant : {FILES['vehicules']}")
    df_veh = _clean_vehicules(_read_csv_any(FILES["vehicules"]))
    _write_clean(df_veh, "Vehicules_2024_clean.csv")

    # USAGERS
    if not FILES["usagers"].exists():
        raise FileNotFoundError(f"Fichier manquant : {FILES['usagers']}")
    df_usa = _clean_usagers(_read_csv_any(FILES["usagers"]))
    _write_clean(df_usa, "Usagers_2024_clean.csv")

if __name__ == "__main__":
    main()
