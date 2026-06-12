"""check_sims2.py — run from C:\SRGEC_SIMS"""
from pathlib import Path

print("=== ROOT APP.PY ===")
app = Path("app.py").read_text(encoding="utf-8", errors="ignore")
print(app[:2000])

print("\n=== MODULE_HOME.PY first 50 lines ===")
mh = Path("pages/module_home.py").read_text(encoding="utf-8", errors="ignore")
lines = mh.split("\n")
for i, l in enumerate(lines[:50], 1):
    print(f"{i:3}: {l}")
