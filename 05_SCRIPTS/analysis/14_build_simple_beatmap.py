import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
project = json.loads((ROOT/"01_CONFIG/project_config.json").read_text(encoding="utf-8"))
bpm = project["bpm"]
duration = project["song_duration_sec"]
beat_sec = 60.0 / bpm
beats = []
t = 0.0
i = 1
while t <= duration:
    beats.append({"beat": i, "t": round(t, 3)})
    i += 1
    t += beat_sec
out = ROOT/"03_WORK/beatmaps/simple_beatmap.json"
out.write_text(json.dumps({"bpm": bpm, "beat_sec": beat_sec, "beats": beats}, indent=2), encoding="utf-8")
print(f"Wrote {out}")
