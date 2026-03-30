import json, shutil, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
log = ROOT/"03_WORK/logs/02_prepare_inputs.log"
paths_cfg = json.loads((ROOT/"01_CONFIG/paths_config.json").read_text(encoding="utf-8"))
ffprobe = paths_cfg.get("ffprobe", "ffprobe")


def w(m):
    print(m)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f: f.write(m+"\n")


def norm(folder, patterns, target):
    for pat in patterns:
        for f in sorted(folder.glob(pat)):
            dst = folder/target
            if f.resolve() != dst.resolve():
                shutil.copy2(f, dst)
                w(f"Copied {f.name} -> {dst.name}")
            else:
                w(f"Already normalized: {dst.name}")
            return


def probe_video_metadata(video_path):
    if not video_path.exists():
        return {}
    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,duration,width,height",
        "-of", "json",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        payload = json.loads(res.stdout)
        stream = (payload.get("streams") or [{}])[0]
        fps_raw = stream.get("r_frame_rate", "30/1")
        try:
            n, d = fps_raw.split("/")
            fps = float(n) / float(d)
        except Exception:
            fps = 30.0
        return {
            "fps_raw": fps_raw,
            "fps": round(fps, 3),
            "duration_sec": round(float(stream.get("duration", 0.0)), 3),
            "width": int(stream.get("width", 1280)),
            "height": int(stream.get("height", 720))
        }
    except Exception as ex:
        w(f"Warning: ffprobe failed ({ex})")
        return {}


audio = ROOT/"02_INPUT/audio"; video = ROOT/"02_INPUT/video"; images = ROOT/"02_INPUT/images"
norm(audio, ["*.wav","*.mp3","*.flac","*.m4a","*.aac"], "song.wav")
norm(video, ["*.mp4","*.mov","*.mkv"], "clip.mp4")
norm(images, ["*.png","*.jpg","*.jpeg","*.webp"], "source_still.png")
video_meta = probe_video_metadata(video/"clip.mp4")
summary = {
    "audio": str((audio/"song.wav")) if (audio/"song.wav").exists() else None,
    "video": str((video/"clip.mp4")) if (video/"clip.mp4").exists() else None,
    "image": str((images/"source_still.png")) if (images/"source_still.png").exists() else None,
    "video_metadata": video_meta
}
(ROOT/"03_WORK/prepared_inputs.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
w("Prepared inputs summary written.")
