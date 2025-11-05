import requests
from pathlib import Path

#Dossier de sortie
RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

#URLs des fichiers CSV
FILES = {
    "Caract_2024.csv": "https://www.data.gouv.fr/fr/datasets/r/83f0fb0e-e0ef-47fe-93dd-9aaee851674a",
    "Lieux_2024.csv": "https://www.data.gouv.fr/fr/datasets/r/228b3cda-fdfb-4677-bd54-ab2107028d2d",
    "Vehicules_2024.csv": "https://www.data.gouv.fr/fr/datasets/r/fd30513c-6b11-4a56-b6dc-5ac87728794b",
    "Usagers_2024.csv": "https://www.data.gouv.fr/fr/datasets/r/f57b1f58-386d-4048-8f78-2ebe435df868",
}

def download_csv_files():
    """Télécharge les 4 fichiers CSV dans data/raw"""
    for name, url in FILES.items():
        dest = RAW_DIR / name
        if dest.exists():
            print(f"✔ {name} déjà présent")
            continue
        print(f"Téléchargement de {name}...")
        r = requests.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
        print(f"✔ {name} téléchargé dans {dest}")

if __name__ == "__main__":
    download_csv_files()
