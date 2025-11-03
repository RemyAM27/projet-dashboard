from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / "data" / "accidents.sqlite"
DEPT_GEOJSON = BASE_DIR / "data" / "geo" / "departements.geojson"
