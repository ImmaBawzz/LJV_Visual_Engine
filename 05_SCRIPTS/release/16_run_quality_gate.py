import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "03_WORK" / "reports" / "quality_gate_report.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_ffprobe(ffprobe_path: str, target: Path, entries: str) -> dict:
    cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        entries,
        "-of",
        "json",
        str(target),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def aspect_ratio(width: int, height: int) -> float:
    if height == 0:
        return 0.0
    return width / height


def roughly_equal(a: float, b: float, tolerance: float) -> bool:
    return abs(a - b) <= tolerance


def probe_media(ffprobe_path: str, file_path: Path) -> dict:
    payload = run_ffprobe(
        ffprobe_path,
        file_path,
        "stream=index,codec_type,codec_name,width,height,duration:format=duration,bit_rate",
    )
    streams = payload.get("streams", [])
    fmt = payload.get("format", {})
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    duration = float(video.get("duration") or fmt.get("duration") or 0.0)
    return {
        "duration_sec": round(duration, 3),
        "width": int(video.get("width", 0) or 0),
        "height": int(video.get("height", 0) or 0),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
        "has_audio": bool(audio),
        "bit_rate": int(fmt.get("bit_rate", 0) or 0),
    }


def main() -> int:
    report = {
        "status": "PASS",
        "errors": [],
        "warnings": [],
        "checks": [],
        "outputs": [],
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

    paths_cfg = load_json(ROOT / "01_CONFIG" / "paths_config.json")
    project_cfg = load_json(ROOT / "01_CONFIG" / "project_config.json")
    ffprobe = paths_cfg.get("ffprobe", "ffprobe")
    song_duration = float(project_cfg.get("song_duration_sec", 0))

    expected_outputs = [
        {
            "label": "master_clean",
            "path": ROOT / "04_OUTPUT" / "youtube_16x9" / "master_clean.mp4",
            "aspect": 16 / 9,
        },
        {
            "label": "master_lyrics",
            "path": ROOT / "04_OUTPUT" / "youtube_16x9" / "master_lyrics.mp4",
            "aspect": 16 / 9,
        },
        {
            "label": "master_softsubs",
            "path": ROOT / "04_OUTPUT" / "youtube_16x9" / "master_softsubs.mp4",
            "aspect": 16 / 9,
        },
        {
            "label": "vertical_lyrics",
            "path": ROOT / "04_OUTPUT" / "vertical_9x16" / "vertical_lyrics.mp4",
            "aspect": 9 / 16,
        },
        {
            "label": "square_lyrics",
            "path": ROOT / "04_OUTPUT" / "square_1x1" / "square_lyrics.mp4",
            "aspect": 1.0,
        },
    ]

    for target in expected_outputs:
        file_path = target["path"]
        rel_path = str(file_path.relative_to(ROOT))
        if not file_path.exists():
            add_check("required_output", "FAIL", f"Missing required output: {rel_path}")
            report["outputs"].append({"path": rel_path, "exists": False})
            continue

        media = probe_media(ffprobe, file_path)
        size_bytes = file_path.stat().st_size
        report["outputs"].append(
            {
                "path": rel_path,
                "exists": True,
                "size_bytes": size_bytes,
                "media": media,
            }
        )

        if size_bytes < 1_000_000:
            add_check("output_size", "FAIL", f"{rel_path} is unexpectedly small ({size_bytes} bytes)")
        else:
            add_check("output_size", "PASS", f"{rel_path} size looks valid")

        if not media["has_audio"]:
            add_check("audio_track", "FAIL", f"{rel_path} has no audio stream")
        else:
            add_check("audio_track", "PASS", f"{rel_path} includes an audio stream")

        if song_duration > 0:
            diff = abs(media["duration_sec"] - song_duration)
            if diff > 2.5:
                add_check("duration_match", "FAIL", f"{rel_path} differs from song by {diff:.3f}s")
            elif diff > 1.0:
                add_check("duration_match", "WARN", f"{rel_path} differs from song by {diff:.3f}s")
            else:
                add_check("duration_match", "PASS", f"{rel_path} duration within tolerance")

        ratio = aspect_ratio(media["width"], media["height"])
        if media["width"] == 0 or media["height"] == 0:
            add_check("video_dimensions", "FAIL", f"{rel_path} has invalid dimensions")
        elif roughly_equal(ratio, target["aspect"], 0.03):
            add_check("video_aspect", "PASS", f"{rel_path} aspect ratio is correct")
        else:
            add_check(
                "video_aspect",
                "FAIL",
                f"{rel_path} aspect ratio mismatch (got {ratio:.4f}, expected {target['aspect']:.4f})",
            )

    teaser_files = sorted((ROOT / "04_OUTPUT" / "teasers").glob("*.mp4"))
    if not teaser_files:
        add_check("teasers", "FAIL", "No teaser files found in 04_OUTPUT/teasers")
    else:
        add_check("teasers", "PASS", f"Found {len(teaser_files)} teaser file(s)")

    for teaser in teaser_files:
        rel_path = str(teaser.relative_to(ROOT))
        media = probe_media(ffprobe, teaser)
        if not media["has_audio"]:
            add_check("teaser_audio", "FAIL", f"{rel_path} has no audio stream")
        if media["duration_sec"] < 8 or media["duration_sec"] > 45:
            add_check("teaser_duration", "WARN", f"{rel_path} duration {media['duration_sec']:.3f}s is unusual")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")

    if report["status"] == "FAIL":
        print("Quality gate failed.")
        return 2

    print(f"Quality gate complete: {report['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())