"""After a test run, scan game.log for anything related to the empty_vehicle_highlight mod.
Usage: .venv/Scripts/python.exe tools/check_log.py
"""
import re
from pathlib import Path

LOG = Path.home() / "Documents" / "My Games" / "gates of hell" / "log" / "game.log"
KEYS = re.compile(r"(?i)empty_vehicle_highlight|evh_|barrel1|interaction_entity|"
                  r"invalid parameter|unknown (condition|instruction)|"
                  r"Mod: activate|Mods applied|failed to load mod")

text = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
print(f"{LOG}  ({len(text)} lines)")
hits = [(i + 1, l) for i, l in enumerate(text) if KEYS.search(l)]
for n, l in hits[:200]:
    print(f"{n:6d}: {l[:220]}")
print(f"-- {len(hits)} matching lines")
