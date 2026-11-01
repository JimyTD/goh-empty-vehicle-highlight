"""Copy mod/empty_vehicle_highlight into <game>/mods/ (replacing the old copy).
Game folder: env GOH_DIR, else the default below.
Usage: python tools/install.py
"""
import os
import shutil
from pathlib import Path

GAME = Path(os.environ.get("GOH_DIR", r"F:\SteamLibrary\steamapps\common\Call to Arms - Gates of Hell"))
SRC = Path(__file__).resolve().parent.parent / "mod" / "empty_vehicle_highlight"
DST = GAME / "mods" / SRC.name

if not (GAME / "mods").is_dir():
    raise SystemExit(f"mods folder not found: {GAME / 'mods'} (set GOH_DIR)")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
n = sum(1 for _ in DST.rglob("*") if _.is_file())
print(f"installed {n} files -> {DST}")
