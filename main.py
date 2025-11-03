# main.py
# Fichier principal du projet

from get_data import download_csv_files

if __name__ == "__main__":
    print("=== Projet Dashboard ===")
    print("Téléchargement des données...")
    download_csv_files()
    print("Données prêtes dans data/raw/")
