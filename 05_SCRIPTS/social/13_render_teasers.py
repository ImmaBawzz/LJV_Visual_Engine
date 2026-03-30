import json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ffmpeg = json.loads((ROOT/"01_CONFIG/paths_config.json").read_text(encoding="utf-8"))["ffmpeg"]
src = ROOT/"04_OUTPUT/youtube_16x9/master_lyrics.mp4"
cfg = json.loads((ROOT/"06_TEMPLATES/json/teaser_timeline_template.json").read_text(encoding="utf-8"))
for clip in cfg["clips"]:
    out = ROOT/"04_OUTPUT/teasers"/f"{clip['name']}.mp4"
    cmd = [ffmpeg, "-y", "-ss", str(clip["start"]), "-i", str(src), "-t", str(clip["duration"]), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "256k", str(out)]
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)
print("Teasers complete.")
