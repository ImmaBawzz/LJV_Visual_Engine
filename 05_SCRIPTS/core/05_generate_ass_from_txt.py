import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TIMED_SRT_PATH = ROOT / "02_INPUT/lyrics/lyrics_timed.srt"
RAW_TIMED_SRT_PATH = ROOT / "02_INPUT/lyrics/lyrics_timed.pre_offset.srt"
RAW_LYRICS_PATH = ROOT / "02_INPUT/lyrics/lyrics_raw.txt"
ASS_OUTPUT_PATH = ROOT / "02_INPUT/lyrics/lyrics_styled.ass"
PROJECT_CONFIG_PATH = ROOT / "01_CONFIG/project_config.json"
STYLE_CONFIG_PATH = ROOT / "01_CONFIG/lyric_style_presets.json"
TIMELINE_PATH = ROOT / "03_WORK/sections/timeline.json"

DEFAULT_PRESENTATION = {
    "lead_in_ms": 140,
    "lead_out_ms": 80,
    "max_phrase_words": 10,
    "max_phrase_chars": 44,
    "display_line_chars": 30,
    "min_phrase_duration_sec": 0.95,
}

BREAK_WORDS = {
    "and",
    "but",
    "while",
    "when",
    "where",
    "now",
    "every",
    "from",
    "like",
    "with",
    "that",
}

SRT_TIMESTAMP_RE = re.compile(r"(\d+):(\d{2}):(\d{2})[,\.](\d{3})")


def sec_to_ass(value):
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = int(value % 60)
    centiseconds = int(round((value - int(value)) * 100))
    if centiseconds == 100:
        seconds += 1
        centiseconds = 0
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"


def sec_to_srt(value):
    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = int(value % 60)
    milliseconds = int(round((value - int(value)) * 1000))
    if milliseconds == 1000:
        seconds += 1
        milliseconds = 0
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def srt_to_sec(value):
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


def normalize_text(value):
    lowered = value.lower().replace("&", " and ")
    lowered = re.sub(r"\([^)]*\)", " ", lowered)
    lowered = re.sub(r"[^a-z0-9'\s]+", " ", lowered)
    lowered = lowered.replace("'", "")
    return re.sub(r"\s+", " ", lowered).strip()


def parse_blocks(text):
    blocks = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if lines:
            blocks.append(lines)
    return blocks


def load_json(path, default=None):
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def load_srt_cues(path):
    blocks = parse_blocks(path.read_text(encoding="utf-8-sig"))
    cues = []
    for block in blocks:
        if len(block) < 2:
            raise ValueError(f"Malformed SRT block: {' | '.join(block)}")

        if re.fullmatch(r"\d+", block[0]):
            timeline_index = 1
            text_lines = block[2:]
        else:
            timeline_index = 0
            text_lines = block[1:]

        if len(block) <= timeline_index or "-->" not in block[timeline_index]:
            raise ValueError(f"Missing SRT timeline in block: {' | '.join(block)}")

        start_raw, end_raw = [part.strip() for part in block[timeline_index].split("-->", 1)]
        start = srt_to_sec(start_raw)
        end = srt_to_sec(end_raw)
        if end <= start:
            raise ValueError(f"Cue end must be after start: {block[timeline_index]}")

        text = "\n".join(text_lines).strip()
        if not text:
            continue
        cues.append({"start": start, "end": end, "text": text})

    if not cues:
        raise ValueError(f"No cues found in {path}")
    return cues


def resolve_timing_source_path():
    if RAW_TIMED_SRT_PATH.exists() and RAW_TIMED_SRT_PATH.read_text(encoding="utf-8-sig").strip():
        return RAW_TIMED_SRT_PATH
    return TIMED_SRT_PATH


def write_srt_cues(path, cues):
    output = []
    for index, cue in enumerate(cues, start=1):
        output.extend(
            [
                str(index),
                f"{sec_to_srt(cue['start'])} --> {sec_to_srt(cue['end'])}",
                *cue["text"].splitlines(),
                "",
            ]
        )
    path.write_text("\n".join(output), encoding="utf-8")


def word_count(text):
    return max(len(re.findall(r"[A-Za-z0-9']+", text)), 1)


def phrase_fits(text, max_words, max_chars):
    single_line = " ".join(text.split())
    return word_count(single_line) <= max_words and len(single_line) <= max_chars


def split_clause_chunks(text):
    pieces = []
    for match in re.finditer(r"[^,;:]+(?:[,;:]|$)", text):
        clause = " ".join(match.group(0).split()).strip()
        if clause:
            pieces.append(clause)
    return pieces or [" ".join(text.split())]


def choose_break_index(words):
    if len(words) <= 1:
        return 1

    midpoint = len(words) // 2
    min_side = 2 if len(words) >= 5 else 1
    candidates = []
    for index in range(1, len(words)):
        if index < min_side or len(words) - index < min_side:
            continue
        previous = words[index - 1].lower().rstrip(",;:")
        current = words[index].lower().rstrip(",;:")
        if words[index - 1].endswith((",", ";", ":")):
            candidates.append(index)
        elif current in BREAK_WORDS or previous in BREAK_WORDS:
            candidates.append(index)

    if candidates:
        return min(candidates, key=lambda value: abs(value - midpoint))
    return max(min_side, min(len(words) - min_side, midpoint))


def split_phrase_text(text, max_words, max_chars):
    single_line = " ".join(text.split())
    if phrase_fits(single_line, max_words, max_chars):
        return [single_line]

    clauses = split_clause_chunks(single_line)
    if len(clauses) > 1:
        packed = []
        current = []
        for clause in clauses:
            candidate = " ".join(current + [clause]).strip()
            if current and not phrase_fits(candidate, max_words, max_chars):
                packed.extend(split_phrase_text(" ".join(current), max_words, max_chars))
                current = [clause]
            else:
                current.append(clause)
        if current:
            packed.extend(split_phrase_text(" ".join(current), max_words, max_chars))
        return packed

    words = single_line.split()
    if len(words) <= 1:
        return [single_line]

    break_index = choose_break_index(words)
    break_index = max(1, min(len(words) - 1, break_index))
    left = " ".join(words[:break_index])
    right = " ".join(words[break_index:])
    return split_phrase_text(left, max_words, max_chars) + split_phrase_text(right, max_words, max_chars)


def merge_phrases_for_duration(phrases, total_duration, min_duration):
    merged = list(phrases)
    while len(merged) > 1 and total_duration < len(merged) * min_duration:
        merged[-2] = f"{merged[-2]} {merged[-1]}".strip()
        merged.pop()
    return merged


def allocate_durations(total_duration, weights, min_duration):
    if len(weights) == 1:
        return [max(total_duration, min_duration)]

    total_weight = float(sum(weights)) or 1.0
    durations = [total_duration * (weight / total_weight) for weight in weights]

    for index, duration in enumerate(list(durations)):
        if duration >= min_duration:
            continue

        deficit = min_duration - duration
        durations[index] = min_duration
        donors = [i for i, value in enumerate(durations) if i != index and value > min_duration]
        while deficit > 1e-6 and donors:
            donor = max(donors, key=lambda candidate: durations[candidate])
            available = durations[donor] - min_duration
            if available <= 1e-6:
                donors.remove(donor)
                continue
            transfer = min(deficit, available)
            durations[donor] -= transfer
            deficit -= transfer

    scale = total_duration / (sum(durations) or 1.0)
    return [duration * scale for duration in durations]


def wrap_display_line(text, limit):
    single_line = " ".join(text.split())
    if len(single_line) <= limit:
        return [single_line]

    words = single_line.split()
    if len(words) <= 1:
        return [single_line]

    min_side = 2 if len(words) >= 5 else 1
    best_index = None
    best_score = None
    for index in range(1, len(words)):
        if index < min_side or len(words) - index < min_side:
            continue

        left = " ".join(words[:index])
        right = " ".join(words[index:])
        overflow = max(0, len(left) - limit) + max(0, len(right) - limit)
        balance = abs(len(left) - len(right))
        bonus = 0
        if words[index - 1].endswith((",", ";", ":")):
            bonus -= 4
        if words[index].lower().rstrip(",;:") in BREAK_WORDS:
            bonus -= 2
        if words[index - 1].lower().rstrip(",;:") in BREAK_WORDS:
            bonus -= 1

        score = overflow * 10 + balance + bonus
        if best_score is None or score < best_score:
            best_score = score
            best_index = index

    break_index = best_index or choose_break_index(words)
    break_index = max(1, min(len(words) - 1, break_index))
    return [" ".join(words[:break_index]), " ".join(words[break_index:])]


def format_display_text(text, display_line_chars):
    clean_text = " ".join(text.split())
    wrapped = wrap_display_line(clean_text, display_line_chars)
    if len(wrapped) <= 2:
        return "\n".join(line for line in wrapped if line)
    return "\n".join([wrapped[0], " ".join(wrapped[1:])])


def apply_text_overrides(cues, overrides):
    if not overrides:
        return cues

    override_map = {}
    for override in overrides:
        match_text = normalize_text(override.get("match_text", ""))
        if match_text:
            override_map[match_text] = override

    updated = []
    for cue in cues:
        override = override_map.get(normalize_text(cue["text"]))
        if override:
            start = float(override.get("start_sec", cue["start"]))
            end = float(override.get("end_sec", cue["end"]))
            updated.append({**cue, "start": start, "end": max(end, start + 0.2)})
        else:
            updated.append(dict(cue))
    return updated


def shape_cues(cues, presentation, overrides):
    lead_in_sec = float(presentation.get("lead_in_ms", 140)) / 1000.0
    lead_out_sec = float(presentation.get("lead_out_ms", 80)) / 1000.0
    max_phrase_words = int(presentation.get("max_phrase_words", 10))
    max_phrase_chars = int(presentation.get("max_phrase_chars", 44))
    display_line_chars = int(presentation.get("display_line_chars", 30))
    min_phrase_duration = float(presentation.get("min_phrase_duration_sec", 0.95))

    shaped = []
    base_cues = apply_text_overrides(cues, overrides)
    for cue in base_cues:
        plain_text = " ".join(cue["text"].split())
        phrases = split_phrase_text(plain_text, max_phrase_words, max_phrase_chars)
        phrases = merge_phrases_for_duration(phrases, cue["end"] - cue["start"], min_phrase_duration)
        durations = allocate_durations(
            cue["end"] - cue["start"],
            [word_count(phrase) for phrase in phrases],
            min_phrase_duration,
        )

        cursor = cue["start"]
        for index, phrase in enumerate(phrases):
            next_cursor = cue["end"] if index == len(phrases) - 1 else cursor + durations[index]
            shaped.append(
                {
                    "start": cursor,
                    "end": max(next_cursor, cursor + min_phrase_duration),
                    "text": format_display_text(phrase, display_line_chars),
                }
            )
            cursor = next_cursor

    adjusted = []
    previous_end = 0.0
    for index, cue in enumerate(shaped):
        next_start = shaped[index + 1]["start"] if index + 1 < len(shaped) else None
        start = max(0.0, cue["start"] - lead_in_sec)
        start = max(start, previous_end)
        end = cue["end"] + lead_out_sec
        if next_start is not None:
            end = min(end, max(start + min_phrase_duration, next_start - 0.03))
        end = max(end, start + min_phrase_duration)
        adjusted.append({"start": start, "end": end, "text": cue["text"]})
        previous_end = end

    return adjusted


def split_display_segments(text, limit):
    segments = []
    for line in text.splitlines():
        clean_line = " ".join(line.split())
        if not clean_line:
            continue
        if len(clean_line) <= limit:
            segments.append(clean_line)
        else:
            segments.extend(wrap_display_line(clean_line, limit))
    return segments or [""]


def allocate_centiseconds(total_cs, parts):
    total_cs = max(total_cs, len(parts))
    base = total_cs // len(parts)
    remainder = total_cs % len(parts)
    return [base + (1 if index < remainder else 0) for index in range(len(parts))]


def karaoke_text(display_text, line_duration, preset, display_line_chars):
    wrapped = split_display_segments(display_text, display_line_chars)
    segments = []
    total_tokens = sum(len(segment.split()) for segment in wrapped)
    total_tokens = max(total_tokens, 1)
    token_cs = allocate_centiseconds(max(1, int(round(line_duration * 100))), [None] * total_tokens)
    cursor = 0

    for segment in wrapped:
        words = segment.split()
        rendered_words = []
        for word in words:
            rendered_words.append(f"{{\\kf{token_cs[cursor]}}}{word}")
            cursor += 1
        segments.append(" ".join(rendered_words))

    event_tags = [f"\\fad({preset.get('fad_in_ms', 180)},{preset.get('fad_out_ms', 220)})"]
    blur = preset.get("blur")
    if blur:
        event_tags.append(f"\\blur{blur}")
    return "{" + "".join(event_tags) + "}" + r"\N".join(segments)


def style_name(style_key):
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", style_key).strip("_")
    return safe_name or "Lyrics"


def build_header(style_presets, used_style_keys):
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1280",
        "PlayResY: 720",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
    ]

    for key in used_style_keys:
        preset = style_presets[key]
        lines.append(
            "Style: "
            + ",".join(
                [
                    style_name(key),
                    str(preset.get("font", "Georgia")),
                    str(preset.get("fontsize", 36)),
                    str(preset.get("primary_colour", "&H00FFFFFF")),
                    str(preset.get("secondary_colour", preset.get("primary_colour", "&H00FFFFFF"))),
                    str(preset.get("outline_colour", "&H00101010")),
                    str(preset.get("back_colour", "&H00000000")),
                    str(int(preset.get("bold", 0))),
                    str(int(preset.get("italic", 0))),
                    "0",
                    "0",
                    str(preset.get("scale_x", 100)),
                    str(preset.get("scale_y", 100)),
                    str(preset.get("spacing", 0)),
                    "0",
                    str(preset.get("border_style", 1)),
                    str(preset.get("outline", 2)),
                    str(preset.get("shadow", 0)),
                    str(preset.get("alignment", 2)),
                    str(preset.get("margin_l", 80)),
                    str(preset.get("margin_r", 80)),
                    str(preset.get("margin_v", 60)),
                    "1",
                ]
            )
        )

    lines.extend(["", "[Events]", "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text"])
    return "\n".join(lines) + "\n"


def load_timeline_sections():
    timeline = load_json(TIMELINE_PATH, {"sections": []})
    return timeline.get("sections", [])


def resolve_style_key(cue, sections, project, style_presets):
    default_style = project.get("lyric_style_default", "spotify_clean")
    cue_time = cue["start"] + min(0.05, max(0.0, cue["end"] - cue["start"]))
    for section in sections:
        if section.get("start", 0) <= cue_time < section.get("end", 0):
            section_style = section.get("lyric_style", default_style) or default_style
            return section_style if section_style in style_presets else default_style
    return default_style if default_style in style_presets else next(iter(style_presets))


def build_events_from_cues(cues, style_presets, sections, project, presentation):
    events = []
    used_styles = []
    display_line_chars = int(presentation.get("display_line_chars", 30))

    for cue in cues:
        cue_style_key = resolve_style_key(cue, sections, project, style_presets)
        cue_preset = style_presets[cue_style_key]
        if cue_style_key not in used_styles:
            used_styles.append(cue_style_key)
        ass_text = karaoke_text(cue["text"], cue["end"] - cue["start"], cue_preset, display_line_chars)
        events.append(
            f"Dialogue: 0,{sec_to_ass(cue['start'])},{sec_to_ass(cue['end'])},{style_name(cue_style_key)},,0,0,0,,{ass_text}"
        )

    return used_styles, events


def build_auto_cues(duration, raw_blocks):
    cues = []
    segment_duration = duration / max(len(raw_blocks), 1)
    for block_index, block_lines in enumerate(raw_blocks):
        block_start = block_index * segment_duration + min(0.2, segment_duration * 0.1)
        block_end = (block_index + 1) * segment_duration - min(0.2, segment_duration * 0.1)
        block_end = max(block_end, block_start + 0.8)
        weights = [word_count(line) for line in block_lines]
        total_weight = sum(weights) or 1
        cursor = block_start

        for line, weight in zip(block_lines, weights):
            line_duration = max(0.8, (block_end - block_start) * (weight / total_weight))
            line_end = min(block_end, cursor + line_duration)
            line_end = max(line_end, cursor + 0.8)
            cues.append({"start": cursor, "end": line_end, "text": line})
            cursor = line_end

    return cues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--preset", default=None)
    parser.add_argument("--timing-source", choices=["auto", "srt", "auto-if-missing"], default="auto-if-missing")
    args = parser.parse_args()

    project = load_json(PROJECT_CONFIG_PATH)
    styles = load_json(STYLE_CONFIG_PATH)
    presentation = {**DEFAULT_PRESENTATION, **project.get("subtitle_presentation", {})}
    duration = args.duration or project["song_duration_sec"]
    sections = load_timeline_sections()

    if args.preset:
        project["lyric_style_default"] = args.preset

    timing_source_path = resolve_timing_source_path()
    use_timed_srt = args.timing_source == "srt" or (
        args.timing_source == "auto-if-missing"
        and timing_source_path.exists()
        and timing_source_path.read_text(encoding="utf-8-sig").strip()
    )

    if use_timed_srt:
        source_cues = load_srt_cues(timing_source_path)
    else:
        raw_blocks = parse_blocks(RAW_LYRICS_PATH.read_text(encoding="utf-8"))
        source_cues = build_auto_cues(duration, raw_blocks)

    shaped_cues = shape_cues(source_cues, presentation, project.get("lyric_timing_overrides", []))
    write_srt_cues(TIMED_SRT_PATH, shaped_cues)

    used_style_keys, events = build_events_from_cues(shaped_cues, styles, sections, project, presentation)
    header = build_header(styles, used_style_keys)
    ASS_OUTPUT_PATH.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    print(f"Lyrics ASS generated from timing source: {timing_source_path.relative_to(ROOT)}")


if __name__ == "__main__":
    raise SystemExit(main())
