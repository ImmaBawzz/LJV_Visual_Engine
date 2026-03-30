import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "03_WORK/reports"
required = [
    ROOT/"04_OUTPUT/youtube_16x9/master_clean.mp4",
    ROOT/"04_OUTPUT/youtube_16x9/master_lyrics.mp4",
    ROOT/"04_OUTPUT/youtube_16x9/master_softsubs.mp4",
    ROOT/"04_OUTPUT/vertical_9x16/vertical_lyrics.mp4",
    ROOT/"04_OUTPUT/square_1x1/square_lyrics.mp4",
]
teasers = list((ROOT/"04_OUTPUT/teasers").glob("*.mp4"))


def load_optional_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

report = {
    "required_outputs": [],
    "teasers_found": [str(p.relative_to(ROOT)) for p in teasers],
    "preflight": load_optional_json(REPORTS/"preflight_validation_report.json"),
    "quality_gate": load_optional_json(REPORTS/"quality_gate_report.json"),
    "status": "PASS"
}
for p in required:
    exists = p.exists()
    report["required_outputs"].append({"path": str(p.relative_to(ROOT)), "exists": exists})
    if not exists:
        report["status"] = "FAIL"

for gate_name in ["preflight", "quality_gate"]:
    gate = report.get(gate_name)
    if gate and gate.get("status") == "FAIL":
        report["status"] = "FAIL"
    elif gate and gate.get("status") == "WARN" and report["status"] != "FAIL":
        report["status"] = "WARN"

out = ROOT/"03_WORK/reports/release_readiness_report.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"Wrote {out}")
