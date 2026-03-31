import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "03_WORK" / "reports" / "quality_gate_report.json"
TIMED_SRT_PATH = ROOT / "02_INPUT" / "lyrics" / "lyrics_timed.srt"
ALIGNMENT_REPORT_PATH = ROOT / "03_WORK" / "analysis" / "lyrics_alignment_report.json"

SRT_TIMESTAMP_RE = re.compile(r"(\d+):(\d{2}):(\d{2})[,\.](\d{3})")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def srt_timestamp_to_sec(value: str) -> float:
    match = SRT_TIMESTAMP_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Invalid SRT timestamp: {value}")
    hours, minutes, seconds, milliseconds = match.groups()
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds) / 1000.0
    )


def parse_srt(path: Path) -> list:
    blocks = path.read_text(encoding="utf-8").replace("\r\n", "\n").strip().split("\n\n")
    cues = []

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        # Support common SRT variants with and without explicit cue index line.
        if "-->" in lines[0]:
            timing_line = lines[0]
            text_lines = lines[1:]
        elif len(lines) > 1 and "-->" in lines[1]:
            timing_line = lines[1]
            text_lines = lines[2:]
        else:
            raise ValueError(f"Could not parse cue timing line in block: {block[:80]}")

        start_raw, end_raw = [part.strip() for part in timing_line.split("-->")]
        start_sec = srt_timestamp_to_sec(start_raw)
        end_sec = srt_timestamp_to_sec(end_raw)
        text = " ".join(text_lines).strip()
        cues.append(
            {
                "start": start_sec,
                "end": end_sec,
                "duration": max(0.0, end_sec - start_sec),
                "text": text,
                "text_lines": text_lines,
            }
        )

    return cues


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
    lyric_qc_cfg = project_cfg.get("lyric_timing_qc", {})
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

    if not TIMED_SRT_PATH.exists():
        add_check("lyric_srt", "FAIL", f"Missing lyric timing source: {TIMED_SRT_PATH.relative_to(ROOT)}")
    else:
        qc_defaults = {
            "min_cue_duration_sec": 1.0,
            "max_cue_duration_sec": 8.0,
            "max_chars_per_second": 20.0,
            "max_words_per_cue": 18,
            "max_chars_per_line": 48,
            "max_lines_per_cue": 2,
            "max_warn_rate": 0.05,
            "max_fail_rate": 0.2,
            "max_review_count": 0,
            "min_alignment_average_score": 92.0,
        }
        qc = {**qc_defaults, **lyric_qc_cfg}

        try:
            cues = parse_srt(TIMED_SRT_PATH)
        except Exception as exc:
            add_check("lyric_srt_parse", "FAIL", f"Could not parse timed SRT: {exc}")
            cues = []

        if cues:
            overlaps = 0
            bad_duration = 0
            cps_over = 0
            words_over = 0
            line_chars_over = 0
            line_count_over = 0
            previous_end = -1.0

            for cue in cues:
                if previous_end >= 0 and cue["start"] + 1e-6 < previous_end:
                    overlaps += 1
                previous_end = cue["end"]

                if cue["duration"] < qc["min_cue_duration_sec"] or cue["duration"] > qc["max_cue_duration_sec"]:
                    bad_duration += 1

                text_len = len(cue["text"])
                cps = text_len / cue["duration"] if cue["duration"] > 0 else float("inf")
                if cps > qc["max_chars_per_second"]:
                    cps_over += 1

                words = len(re.findall(r"[A-Za-z0-9']+", cue["text"]))
                if words > qc["max_words_per_cue"]:
                    words_over += 1

                if len(cue["text_lines"]) > qc["max_lines_per_cue"]:
                    line_count_over += 1
                if any(len(line) > qc["max_chars_per_line"] for line in cue["text_lines"]):
                    line_chars_over += 1

            total = len(cues)
            readability_violations = bad_duration + cps_over + words_over + line_chars_over + line_count_over
            readability_rate = readability_violations / total if total else 0.0

            if overlaps > 0:
                add_check("lyric_monotonic_timing", "FAIL", f"Detected {overlaps} overlapping cue(s)")
            else:
                add_check("lyric_monotonic_timing", "PASS", "No overlapping lyric cues detected")

            if readability_rate > qc["max_fail_rate"]:
                add_check(
                    "lyric_readability",
                    "FAIL",
                    (
                        f"Readability violations exceed fail rate ({readability_rate:.1%}). "
                        f"duration:{bad_duration}, cps:{cps_over}, words:{words_over}, "
                        f"line_chars:{line_chars_over}, line_count:{line_count_over}"
                    ),
                )
            elif readability_rate > qc["max_warn_rate"]:
                add_check(
                    "lyric_readability",
                    "WARN",
                    (
                        f"Readability violations exceed warn rate ({readability_rate:.1%}). "
                        f"duration:{bad_duration}, cps:{cps_over}, words:{words_over}, "
                        f"line_chars:{line_chars_over}, line_count:{line_count_over}"
                    ),
                )
            else:
                add_check(
                    "lyric_readability",
                    "PASS",
                    (
                        f"Readability within thresholds. "
                        f"duration:{bad_duration}, cps:{cps_over}, words:{words_over}, "
                        f"line_chars:{line_chars_over}, line_count:{line_count_over}"
                    ),
                )

        if ALIGNMENT_REPORT_PATH.exists():
            try:
                alignment_report = load_json(ALIGNMENT_REPORT_PATH)
                summary = alignment_report.get("summary", {})
                review_count = int(summary.get("review_count", 0))
                average_score = float(summary.get("average_score", 0.0))

                if review_count > int(qc["max_review_count"]):
                    add_check(
                        "lyric_alignment_review_count",
                        "WARN",
                        f"review_count={review_count} exceeds threshold {qc['max_review_count']}",
                    )
                else:
                    add_check(
                        "lyric_alignment_review_count",
                        "PASS",
                        f"review_count={review_count} within threshold",
                    )

                if average_score < float(qc["min_alignment_average_score"]):
                    add_check(
                        "lyric_alignment_average_score",
                        "WARN",
                        (
                            f"average_score={average_score:.2f} below threshold "
                            f"{qc['min_alignment_average_score']:.2f}"
                        ),
                    )
                else:
                    add_check(
                        "lyric_alignment_average_score",
                        "PASS",
                        f"average_score={average_score:.2f} meets threshold",
                    )
            except Exception as exc:
                add_check("lyric_alignment_report", "WARN", f"Could not parse alignment report: {exc}")
        else:
            add_check(
                "lyric_alignment_report",
                "WARN",
                f"Alignment report missing at {ALIGNMENT_REPORT_PATH.relative_to(ROOT)}",
            )

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