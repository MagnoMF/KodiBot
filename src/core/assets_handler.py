from pathlib import Path

ASSETS_PATH = Path(__file__).resolve().parent.parent / "img"

def get_asset_path(filename):
    if(ASSETS_PATH / filename).exists():
        return ASSETS_PATH / filename
    return False