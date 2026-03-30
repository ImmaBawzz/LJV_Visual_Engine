import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
files = []
for path in (ROOT/"04_OUTPUT").rglob("*"):
    if path.is_file():
        files.append({"path": str(path.relative_to(ROOT)), "size_bytes": path.stat().st_size})
out = ROOT/"04_OUTPUT/delivery_manifest.json"
out.write_text(json.dumps({"files": files}, indent=2), encoding="utf-8")
print(f"Wrote {out}")
