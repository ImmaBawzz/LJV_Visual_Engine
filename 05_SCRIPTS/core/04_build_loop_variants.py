import json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ffmpeg = json.loads((ROOT/"01_CONFIG/paths_config.json").read_text(encoding="utf-8"))["ffmpeg"]
presets = json.loads((ROOT/"01_CONFIG/export_presets.json").read_text(encoding="utf-8"))
project = json.loads((ROOT/"01_CONFIG/project_config.json").read_text(encoding="utf-8"))
primary = project.get("primary_format", "youtube_16x9")
target = presets.get(primary, presets["youtube_16x9"])
target_fps = target.get("fps", 30)
target_w = target.get("width", 1280)
target_h = target.get("height", 720)
src = ROOT/"03_WORK/loops/loop_pingpong.mp4"
out_dir = ROOT/"03_WORK/loops"
variants = {
    "loop_clean.mp4": None,
    "loop_zoom_drift.mp4": f"zoompan=z='min(max(1.0,zoom+0.00015*sin(on/{target_fps})),1.025)':d=1:s={target_w}x{target_h}:fps={target_fps}",
    "loop_glow_breath.mp4": "eq=brightness='0.03*sin(t*0.5)'",
    "loop_vignette_pulse.mp4": "vignette=PI/6+0.02*sin(t*0.4)",
    "loop_climax_lift.mp4": "eq=brightness='0.06+0.02*sin(t*0.7)'"
}
for name, vf in variants.items():
    dst = out_dir/name
    cmd = [ffmpeg, "-y", "-i", str(src)]
    base_vf = f"fps={target_fps},scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2"
    if vf:
        cmd += ["-vf", f"{base_vf},{vf}"]
    else:
        cmd += ["-vf", base_vf]
    cmd += ["-an","-c:v","libx264","-preset","medium","-crf","18",str(dst)]
    print("RUN:", " ".join(cmd))
    subprocess.run(cmd, check=True)
print("Loop variants built.")
