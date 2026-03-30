import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "03_WORK" / "reports" / "preflight_validation_report.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_first(folder: Path, patterns: list[str]) -> Path | None:
    for pattern in patterns:
        matches = sorted(folder.glob(pattern))
        if matches:
            return matches[0]
    return None


def run_ffprobe(ffprobe_path: str, target: Path, stream_selector: str, entries: str) -> dict:
    cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-select_streams",
        stream_selector,
        "-show_entries",
        entries,
        "-of",
        "json",
        str(target),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def parse_fps(value: str) -> float:
    if not value or "/" not in value:
        return 0.0
    num, den = value.split("/", 1)
    try:
        den_f = float(den)
        if den_f == 0:
            return 0.0
        return float(num) / den_f
    except ValueError:
        return 0.0


def main() -> int:
    report = {
        "status": "PASS",
        "errors": [],
        "warnings": [],
        "checks": [],
    }

    def add_check(name: str, status: str, detail: str) -> None:
        report["checks"].append({"name": name, "status": status, "detail": detail})
        if status == "FAIL":
            report["errors"].append({"name": name, "detail": detail})
            report["status"] = "FAIL"
        elif status == "WARN":
            if report["status"] != "FAIL":
                report["status"] = "WARN"
            report["warnings"].append({"name": name, "detail": detail})

    config_dir = ROOT / "01_CONFIG"
    project_cfg_path = config_dir / "project_config.json"
    paths_cfg_path = config_dir / "paths_config.json"

    if not project_cfg_path.exists() or not paths_cfg_path.exists():
        add_check(
            "config_files",
            "FAIL",
            "Missing project_config.json or paths_config.json in 01_CONFIG.",
        )
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {REPORT_PATH}")
        return 2

    project_cfg = load_json(project_cfg_path)
    paths_cfg = load_json(paths_cfg_path)

    for key in ["artist", "title", "song_duration_sec", "section_plan", "export_targets"]:
        if key not in project_cfg:
            add_check("project_config", "FAIL", f"Missing required key: {key}")

    duration_cfg = project_cfg.get("song_duration_sec")
    if isinstance(duration_cfg, (int, float)) and duration_cfg > 0:
        add_check("song_duration_sec", "PASS", f"Configured duration: {duration_cfg:.3f}s")
    else:
        add_check("song_duration_sec", "FAIL", "project_config.song_duration_sec must be > 0")

    for key in ["ffmpeg", "ffprobe"]:
        value = paths_cfg.get(key)
        if value and (Path(value).exists() or shutil.which(value)):
            add_check("paths_config", "PASS", f"{key} is configured and resolvable")
        else:
            add_check("paths_config", "FAIL", f"{key} is missing or not resolvable")

    if paths_cfg.get("font_primary"):
        add_check("paths_config", "PASS", "font_primary is configured")
    else:
        add_check("paths_config", "FAIL", "font_primary is missing")

    required_texts = {
        "artist_name": ROOT / "02_INPUT" / "branding" / "artist_name.txt",
        "title": ROOT / "02_INPUT" / "branding" / "title.txt",
        "lyrics_raw": ROOT / "02_INPUT" / "lyrics" / "lyrics_raw.txt",
    }
    for label, path in required_texts.items():
        if not path.exists():
            add_check("required_input", "FAIL", f"Missing {label}: {path.relative_to(ROOT)}")
            continue
        content = path.read_text(encoding="utf-8", errors="ignore").strip()
        if content:
            add_check("required_input", "PASS", f"{label} present and non-empty")
        else:
            add_check("required_input", "FAIL", f"{label} is empty: {path.relative_to(ROOT)}")

    timed_lyrics_path = ROOT / "02_INPUT" / "lyrics" / "lyrics_timed.srt"
    if timed_lyrics_path.exists() and timed_lyrics_path.read_text(encoding="utf-8", errors="ignore").strip():
        add_check(
            "lyrics_timing",
            "PASS",
            f"Strict timing source found: {timed_lyrics_path.relative_to(ROOT)}",
        )
    else:
        add_check(
            "lyrics_timing",
            "WARN",
            "lyrics_timed.srt is missing or empty; subtitle timing will be auto-generated and may not align strictly with vocals.",
        )

    audio_file = discover_first(
        ROOT / "02_INPUT" / "audio",
        ["song.wav", "*.wav", "*.mp3", "*.flac", "*.m4a", "*.aac"],
    )
    video_file = discover_first(
        ROOT / "02_INPUT" / "video",
        ["clip.mp4", "*.mp4", "*.mov", "*.mkv"],
    )

    if audio_file:
        add_check("audio_source", "PASS", f"Audio source found: {audio_file.relative_to(ROOT)}")
    else:
        add_check("audio_source", "FAIL", "No audio input found in 02_INPUT/audio")

    if video_file:
        add_check("video_source", "PASS", f"Video source found: {video_file.relative_to(ROOT)}")
    else:
        add_check("video_source", "FAIL", "No video input found in 02_INPUT/video")

    ffprobe = paths_cfg.get("ffprobe", "ffprobe")
    if audio_file and video_file and report["status"] != "FAIL":
        try:
            audio_probe = run_ffprobe(ffprobe, audio_file, "a:0", "stream=duration")
            audio_stream = (audio_probe.get("streams") or [{}])[0]
            audio_duration = float(audio_stream.get("duration", 0.0))
            add_check("audio_probe", "PASS", f"Audio duration: {audio_duration:.3f}s")

            if isinstance(duration_cfg, (int, float)):
                diff = abs(audio_duration - float(duration_cfg))
                if diff > 5.0:
                    add_check(
                        "duration_consistency",
                        "FAIL",
                        f"Audio duration differs from config by {diff:.3f}s",
                    )
                elif diff > 2.0:
                    add_check(
                        "duration_consistency",
                        "WARN",
                        f"Audio duration differs from config by {diff:.3f}s",
                    )
                else:
                    add_check(
                        "duration_consistency",
                        "PASS",
                        f"Audio duration within tolerance ({diff:.3f}s)",
                    )

            video_probe = run_ffprobe(
                ffprobe,
                video_file,
                "v:0",
                "stream=width,height,r_frame_rate,duration",
            )
            video_stream = (video_probe.get("streams") or [{}])[0]
            fps = parse_fps(str(video_stream.get("r_frame_rate", "0/1")))
            width = int(video_stream.get("width", 0))
            height = int(video_stream.get("height", 0))
            duration = float(video_stream.get("duration", 0.0))
            add_check(
                "video_probe",
                "PASS",
                f"Video {width}x{height} at {fps:.3f} fps, {duration:.3f}s",
            )

            if width < 640 or height < 360:
                add_check("video_resolution", "WARN", "Input video is below 640x360")
            else:
                add_check("video_resolution", "PASS", "Input video resolution is acceptable")
        except Exception as ex:
            add_check("media_probe", "FAIL", f"ffprobe metadata extraction failed: {ex}")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")

    if report["status"] == "FAIL":
        print("Preflight validation failed.")
        return 2

    print(f"Preflight validation complete: {report['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())