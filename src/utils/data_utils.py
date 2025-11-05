from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from .sqlite_utils import load_join_carac_lieux

def load_geojson_departments(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_accidents(db_path: Path, year: int = 2024) -> pd.DataFrame:
    df = load_join_carac_lieux(db_path, year=year)
    if "dep" in df.columns:
        df["dep"] = df["dep"].astype(str).str.upper().str.strip()
        m_num = df["dep"].str.match(r"^\d+$", na=False)
        df.loc[m_num, "dep"] = df.loc[m_num, "dep"].str.zfill(2)
    if "mois" in df.columns:
        df["mois"] = pd.to_numeric(df["mois"], errors="coerce").astype("Int64")
    return df
