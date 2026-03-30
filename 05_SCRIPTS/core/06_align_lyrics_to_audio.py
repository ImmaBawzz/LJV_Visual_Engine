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
TIMED_SRT_PATH = ROOT / "02_INPUT/lyrics/lyrics_timed.srt"
DEFAULT_AUDIO_PATH = ROOT / "02_INPUT/audio/song.wav"
REPORT_PATH = ROOT / "03_WORK/analysis/lyrics_alignment_report.json"
PATHS_CONFIG_PATH = ROOT / "01_CONFIG/paths_config.json"
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

    return order_score * 0.55 + set_score * 0.25 + prefix_score * 0.1 + suffix_score * 0.1 - length_penalty


def align_line(line_text, transcript_words, start_cursor, search_ahead, search_back):
    line_tokens = tokenize(line_text)
    if not line_tokens:
        return None

    search_start = max(0, start_cursor - search_back)
    max_start = min(len(transcript_words), max(search_start + 1, start_cursor + search_ahead))
    best = None
    base_length = len(line_tokens)
    min_window = max(1, base_length - max(2, base_length // 3))
    max_window = base_length + max(6, base_length // 2)

    for start_index in range(search_start, max_start):
        window_cap = min(len(transcript_words), start_index + max_window)
        for end_index in range(start_index + min_window, window_cap + 1):
            candidate_tokens = [entry["token"] for entry in transcript_words[start_index:end_index]]
            score = score_candidate(line_tokens, candidate_tokens)
            if start_index < start_cursor:
                score -= (start_cursor - start_index) * 0.35
            if best is None or score > best["score"]:
                best = {
                    "score": score,
                    "start_index": start_index,
                    "end_index": end_index - 1,
                    "candidate_text": " ".join(candidate_tokens),
                }

    return best


def retime_lines(lines, transcript_words, search_ahead, min_score):
    aligned = []
    cursor = 0
    for index, line in enumerate(lines, start=1):
        search_back = max(30, len(tokenize(line)) * 2)
        match = align_line(line, transcript_words, cursor, search_ahead, search_back)
        if not match:
            raise ValueError(f"Unable to align lyric line {index}: {line}")

        start_word = transcript_words[match["start_index"]]
        end_word = transcript_words[match["end_index"]]
        aligned.append(
            {
                "index": index,
                "text": line,
                "start": start_word["start"],
                "end": end_word["end"],
                "score": round(match["score"], 2),
                "matched_text": match["candidate_text"],
                "start_index": match["start_index"],
                "end_index": match["end_index"],
                "status": "ok" if match["score"] >= min_score else "review",
            }
        )
        cursor = match["end_index"] + 1

    return enforce_monotonic_times(aligned)


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
    report = {
        "audio_path": str(audio_path.relative_to(ROOT)),
        "model": model_name,
        "transcription": transcription_info,
        "summary": {
            "line_count": len(entries),
            "review_count": sum(1 for entry in entries if entry["status"] != "ok"),
            "first_line_start": entries[0]["start"] if entries else None,
            "last_line_end": entries[-1]["end"] if entries else None,
            "average_score": round(sum(entry["score"] for entry in entries) / len(entries), 2) if entries else None,
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
    write_status("transcribed", f"Collected {len(transcript_words)} timestamped words", {"word_count": len(transcript_words)})
    print(f"Collected {len(transcript_words)} timestamped words")

    aligned = retime_lines(lines, transcript_words, args.search_ahead, args.min_score)
    write_status("aligned", f"Aligned {len(aligned)} lyric lines", {"aligned_line_count": len(aligned)})
    write_srt(aligned, TIMED_SRT_PATH)
    write_report(REPORT_PATH, args.model, audio_path, transcription_info, aligned)

    review_count = sum(1 for entry in aligned if entry["status"] != "ok")
    write_status("complete", "Lyric alignment finished", {"review_count": review_count})
    print(f"Wrote timed lyrics: {TIMED_SRT_PATH.relative_to(ROOT)}")
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