import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
timeline = json.loads((ROOT/"03_WORK/sections/timeline.json").read_text(encoding="utf-8"))
analysis_path = ROOT/"03_WORK/analysis/audio_envelope.json"
reactive_cfg = json.loads((ROOT/"01_CONFIG/reactive_presets.json").read_text(encoding="utf-8"))
project = json.loads((ROOT/"01_CONFIG/project_config.json").read_text(encoding="utf-8"))
preset_name = project.get("reactive_preset", "subtle_emotional")
reactive = reactive_cfg[preset_name]
envelope = json.loads(analysis_path.read_text(encoding="utf-8")) if analysis_path.exists() else {"points":[]}

def avg_norm(start, end):
    pts = [p["norm"] for p in envelope.get("points", []) if start <= p["t"] < end]
    return round(sum(pts)/len(pts), 6) if pts else 0.0

sections = []
for sec in timeline["sections"]:
    start, end = sec["start"], sec["end"]
    sections.append({
        "label": sec["label"],
        "start": start,
        "end": end,
        "duration_sec": round(end - start, 3),
        "source": str((ROOT/"03_WORK/loops"/sec["loop_variant"]).resolve()),
        "output_name": f"section_{sec['label']}.mp4",
        "title": sec.get("title"),
        "lyric_style": sec.get("lyric_style", project["lyric_style_default"]),
        "audio_avg_norm": avg_norm(start, end),
        "reactive": reactive
    })
out = ROOT/"03_WORK/sections/timeline_manifest.json"
out.write_text(json.dumps({"sections": sections}, indent=2), encoding="utf-8")
print(f"Wrote {out}")
