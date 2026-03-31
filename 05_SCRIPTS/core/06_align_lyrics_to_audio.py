import argparse
import json
import os
import re
import traceback
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz
import whisper


ROOT = Path(__file__).resolve().parents[2]
RAW_LYRICS_PATH = ROOT / "02_INPUT/lyrics/lyrics_raw.txt"
RAW_TIMED_SRT_PATH = ROOT / "02_INPUT/lyrics/lyrics_timed.pre_offset.srt"
DEFAULT_AUDIO_PATH = ROOT / "02_INPUT/audio/song.wav"
REPORT_PATH = ROOT / "03_WORK/analysis/lyrics_alignment_report.json"
PATHS_CONFIG_PATH = ROOT / "01_CONFIG/paths_config.json"
PROJECT_CONFIG_PATH = ROOT / "01_CONFIG/project_config.json"
STATUS_PATH = ROOT / "03_WORK/analysis/lyrics_alignment_status.json"


def configure_ffmpeg_path():
    if not PATHS_CONFIG_PATH.exists():
        return

    try:
        paths_config = json.loads(PATHS_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    ffmpeg_path = paths_config.get("ffmpeg")
    if not ffmpeg_path:
        return

    if Path(ffmpeg_path).name == ffmpeg_path and not any(sep in ffmpeg_path for sep in ("/", "\\")):
        return

    ffmpeg_candidate = Path(ffmpeg_path)
    if not ffmpeg_candidate.exists():
        return

    ffmpeg_dir = str(ffmpeg_candidate.resolve().parent)
    existing_path = os.environ.get("PATH", "")
    path_entries = existing_path.split(os.pathsep) if existing_path else []
    if ffmpeg_dir not in path_entries:
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + existing_path if existing_path else ffmpeg_dir


def normalize_text(text):
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().replace("&", " and ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9'\s]+", " ", text)
    text = text.replace("'", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text):
    normalized = normalize_text(text)
    if not normalized:
        return []
    return normalized.split()


def load_project_config():
    if not PROJECT_CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(PROJECT_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_timing_overrides():
    overrides = {}
    for override in load_project_config().get("lyric_timing_overrides", []):
        match_text = normalize_text(override.get("match_text", ""))
        if match_text:
            overrides[match_text] = override
    return overrides


def sec_to_srt(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def load_lyric_lines(path):
    lines = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line:
            lines.append(line)
    if not lines:
        raise ValueError(f"No lyric lines found in {path}")
    return lines


def transcribe_words(audio_path, model_name, device, compute_type, beam_size):
    del compute_type, beam_size

    model = whisper.load_model(model_name, device=device)
    result = model.transcribe(
        str(audio_path),
        language="en",
        word_timestamps=True,
        condition_on_previous_text=False,
        verbose=False,
        fp16=device != "cpu",
        temperature=0,
    )

    words = []
    segment_payload = []
    for segment in result.get("segments", []):
        segment_payload.append(
            {
                "start": float(segment["start"]),
                "end": float(segment["end"]),
                "text": segment.get("text", "").strip(),
            }
        )
        for word in segment.get("words", []):
            if word.get("start") is None or word.get("end") is None:
                continue
            token = normalize_text(word.get("word", ""))
            if not token:
                continue
            words.append(
                {
                    "word": word.get("word", "").strip(),
                    "token": token,
                    "start": float(word["start"]),
                    "end": float(word["end"]),
                    "probability": word.get("probability"),
                }
            )

    if not words:
        raise ValueError("Transcription produced no timestamped words")

    return words, {
        "language": result.get("language", "en"),
        "language_probability": None,
        "duration_after_vad": None,
        "segments": segment_payload,
    }


def score_candidate(line_tokens, candidate_tokens):
    if not line_tokens or not candidate_tokens:
        return -1.0

    line_text = " ".join(line_tokens)
    candidate_text = " ".join(candidate_tokens)
    prefix_len = min(3, len(line_tokens), len(candidate_tokens))
    suffix_len = min(3, len(line_tokens), len(candidate_tokens))

    order_score = fuzz.ratio(line_text, candidate_text)
    set_score = fuzz.token_set_ratio(line_text, candidate_text)
    prefix_score = fuzz.ratio(
        " ".join(line_tokens[:prefix_len]),
        " ".join(candidate_tokens[:prefix_len]),
    )
    suffix_score = fuzz.ratio(
        " ".join(line_tokens[-suffix_len:]),
        " ".join(candidate_tokens[-suffix_len:]),
    )
    length_penalty = abs(len(candidate_tokens) - len(line_tokens)) * 1.5

    score = order_score * 0.55 + set_score * 0.25 + prefix_score * 0.1 + suffix_score * 0.1 - length_penalty

    if len(line_tokens) <= 2:
        exact_window = candidate_tokens[: len(line_tokens)] == line_tokens
        exact_match = candidate_tokens == line_tokens
        token_presence = all(token in candidate_tokens for token in line_tokens)
        oversized_window = max(0, len(candidate_tokens) - max(3, len(line_tokens) + 1))

        if exact_window:
            score += 18
        if exact_match:
            score += 14
        elif token_presence:
            score += 6
        score -= oversized_window * 4

    return score


def align_line(line_text, transcript_words, start_cursor, search_ahead, search_back):
    line_tokens = tokenize(line_text)
    if not line_tokens:
        return None

    search_start = max(0, start_cursor - search_back)
    max_start = min(len(transcript_words), max(search_start + 1, start_cursor + search_ahead))
    best = None
    base_length = len(line_tokens)
    short_line = base_length <= 2

    if short_line:
        min_window = 1
        max_window = min(10, max(4, base_length + 6))
    else:
        min_window = max(1, base_length - max(2, base_length // 3))
        max_window = base_length + max(6, base_length // 2)

    for start_index in range(search_start, max_start):
        window_cap = min(len(transcript_words), start_index + max_window)
        for end_index in range(start_index + min_window, window_cap + 1):
            candidate_tokens = [entry["token"] for entry in transcript_words[start_index:end_index]]
            score = score_candidate(line_tokens, candidate_tokens)
            if start_index < start_cursor:
                penalty_weight = 0.08 if short_line else 0.35
                score -= (start_cursor - start_index) * penalty_weight
            elif short_line:
                score -= (start_index - search_start) * 0.03
            if best is None or score > best["score"]:
                best = {
                    "score": score,
                    "start_index": start_index,
                    "end_index": end_index - 1,
                    "candidate_text": " ".join(candidate_tokens),
                }

    return best


def build_override_entry(index, line_text, override):
    start = float(override.get("start_sec", 0.0))
    end = float(override.get("end_sec", start + 0.2))
    return {
        "index": index,
        "text": line_text,
        "start": start,
        "end": max(end, start + 0.2),
        "score": 100.0,
        "matched_text": "manual override",
        "start_index": None,
        "end_index": None,
        "status": "ok",
        "override_applied": True,
        "timing_source": "override",
        "anchored": True,
    }


def interpolate_unanchored(entries, song_duration):
    if not entries:
        return entries

    index = 0
    while index < len(entries):
        if entries[index].get("anchored"):
            index += 1
            continue

        block_start_index = index
        while index < len(entries) and not entries[index].get("anchored"):
            index += 1
        block_end_index = index

        previous_anchor = entries[block_start_index - 1] if block_start_index > 0 else None
        next_anchor = entries[block_end_index] if block_end_index < len(entries) else None

        block_start = previous_anchor["end"] if previous_anchor else 0.0
        block_end = next_anchor["start"] if next_anchor else song_duration
        if block_end <= block_start:
            fallback_span = max(0.2 * (block_end_index - block_start_index), 0.2)
            block_end = block_start + fallback_span

        block = entries[block_start_index:block_end_index]
        weights = [max(len(tokenize(entry["text"])), 1) for entry in block]
        total_weight = float(sum(weights)) or float(len(block))
        available_duration = max(block_end - block_start, 0.2 * len(block))
        cursor = block_start

        for relative_index, entry in enumerate(block):
            if relative_index == len(block) - 1:
                next_cursor = block_end
            else:
                proportion = weights[relative_index] / total_weight
                next_cursor = cursor + available_duration * proportion
            entry["start"] = cursor
            entry["end"] = max(next_cursor, cursor + 0.2)
            entry["timing_source"] = "interpolated"
            cursor = entry["end"]

    return entries


def retime_lines(lines, transcript_words, search_ahead, min_score, song_duration, timing_overrides):
    aligned = []
    cursor = 0
    for index, line in enumerate(lines, start=1):
        override = timing_overrides.get(normalize_text(line))
        if override:
            aligned.append(build_override_entry(index, line, override))
            continue

        search_back = max(30, len(tokenize(line)) * 2)
        match = align_line(line, transcript_words, cursor, search_ahead, search_back)
        if not match:
            aligned.append(
                {
                    "index": index,
                    "text": line,
                    "start": None,
                    "end": None,
                    "score": 0.0,
                    "matched_text": None,
                    "start_index": None,
                    "end_index": None,
                    "status": "review",
                    "timing_source": "interpolated",
                    "anchored": False,
                }
            )
            continue

        start_word = transcript_words[match["start_index"]]
        end_word = transcript_words[match["end_index"]]
        accepted = match["score"] >= min_score
        aligned.append(
            {
                "index": index,
                "text": line,
                "start": start_word["start"] if accepted else None,
                "end": end_word["end"] if accepted else None,
                "score": round(match["score"], 2),
                "matched_text": match["candidate_text"],
                "start_index": match["start_index"],
                "end_index": match["end_index"],
                "status": "ok" if accepted else "review",
                "timing_source": "match" if accepted else "interpolated",
                "anchored": accepted,
            }
        )
        if accepted:
            cursor = match["end_index"] + 1

    return enforce_monotonic_times(interpolate_unanchored(aligned, song_duration))


def enforce_monotonic_times(entries):
    if not entries:
        return entries

    previous_end = 0.0
    for entry in entries:
        entry["start"] = max(previous_end, entry["start"])
        if entry["end"] <= entry["start"]:
            entry["end"] = entry["start"] + 0.2
        previous_end = entry["end"]

    for index in range(len(entries) - 1):
        current = entries[index]
        nxt = entries[index + 1]
        if current["end"] > nxt["start"]:
            midpoint = (current["start"] + nxt["start"]) / 2
            current["end"] = max(current["start"] + 0.1, midpoint)
            nxt["start"] = max(current["end"], nxt["start"])
            if nxt["end"] <= nxt["start"]:
                nxt["end"] = nxt["start"] + 0.2

    return entries


def write_srt(entries, path):
    output = []
    for index, entry in enumerate(entries, start=1):
        output.extend(
            [
                str(index),
                f"{sec_to_srt(entry['start'])} --> {sec_to_srt(entry['end'])}",
                entry["text"],
                "",
            ]
        )
    path.write_text("\n".join(output), encoding="utf-8")


def write_report(report_path, model_name, audio_path, transcription_info, entries):
    scored_entries = [entry["score"] for entry in entries if entry.get("score") is not None]
    report = {
        "audio_path": str(audio_path.relative_to(ROOT)),
        "model": model_name,
        "transcription": transcription_info,
        "summary": {
            "line_count": len(entries),
            "review_count": sum(1 for entry in entries if entry["status"] != "ok"),
            "first_line_start": entries[0]["start"] if entries else None,
            "last_line_end": entries[-1]["end"] if entries else None,
            "average_score": round(sum(scored_entries) / len(scored_entries), 2) if scored_entries else None,
        },
        "lines": entries,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def write_status(stage, detail, extra=None):
    payload = {
        "stage": stage,
        "detail": detail,
    }
    if extra:
        payload.update(extra)
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", default=str(DEFAULT_AUDIO_PATH))
    parser.add_argument("--model", default="small.en")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--search-ahead", type=int, default=160)
    parser.add_argument("--min-score", type=float, default=72.0)
    args = parser.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    project_config = load_project_config()
    song_duration = float(project_config.get("song_duration_sec", 0.0))
    timing_overrides = load_timing_overrides()

    configure_ffmpeg_path()
    write_status("starting", f"Preparing lyric alignment for {audio_path.name}", {"model": args.model})

    lines = load_lyric_lines(RAW_LYRICS_PATH)
    write_status("lyrics_loaded", f"Loaded {len(lines)} lyric lines", {"line_count": len(lines)})
    print(f"Loaded {len(lines)} lyric lines")
    print(f"Transcribing {audio_path.name} with model {args.model}...")
    transcript_words, transcription_info = transcribe_words(
        audio_path,
        model_name=args.model,
        device=args.device,
        compute_type=args.compute_type,
        beam_size=args.beam_size,
    )
    segment_end = 0.0
    if transcription_info.get("segments"):
        segment_end = float(transcription_info["segments"][-1].get("end", 0.0))
    write_status("transcribed", f"Collected {len(transcript_words)} timestamped words", {"word_count": len(transcript_words)})
    print(f"Collected {len(transcript_words)} timestamped words")

    aligned = retime_lines(
        lines,
        transcript_words,
        args.search_ahead,
        args.min_score,
        song_duration=max(song_duration, segment_end),
        timing_overrides=timing_overrides,
    )
    write_status("aligned", f"Aligned {len(aligned)} lyric lines", {"aligned_line_count": len(aligned)})
    write_srt(aligned, RAW_TIMED_SRT_PATH)
    write_report(REPORT_PATH, args.model, audio_path, transcription_info, aligned)

    review_count = sum(1 for entry in aligned if entry["status"] != "ok")
    write_status("complete", "Lyric alignment finished", {"review_count": review_count})
    print(f"Wrote aligned lyric timing: {RAW_TIMED_SRT_PATH.relative_to(ROOT)}")
    print(f"Wrote alignment report: {REPORT_PATH.relative_to(ROOT)}")
    print(f"Lines flagged for review: {review_count}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        write_status(
            "failed",
            str(exc),
            {
                "traceback": traceback.format_exc(),
            },
        )
        raise