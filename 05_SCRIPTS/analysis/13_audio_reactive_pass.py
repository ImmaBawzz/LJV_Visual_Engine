import wave, audioop, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
audio = ROOT/"02_INPUT/audio/song.wav"
out = ROOT/"03_WORK/analysis/audio_envelope.json"
window_ms = 100
points = []
with wave.open(str(audio), 'rb') as wf:
    fr = wf.getframerate()
    sw = wf.getsampwidth()
    frames_per = max(1, int(fr * window_ms / 1000))
    idx = 0
    while True:
        frames = wf.readframes(frames_per)
        if not frames:
            break
        rms = audioop.rms(frames, sw)
        t = idx * (window_ms / 1000.0)
        points.append({"t": round(t, 3), "rms": rms})
        idx += 1
max_rms = max((p["rms"] for p in points), default=1)
for p in points:
    p["norm"] = round(p["rms"] / max_rms, 6)
out.write_text(json.dumps({"window_ms": window_ms, "max_rms": max_rms, "points": points[:5000]}, indent=2), encoding="utf-8")
print(f"Wrote {out}")
