import argparse, json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TIMED_SRT_PATH = ROOT / "02_INPUT/lyrics/lyrics_timed.srt"
RAW_LYRICS_PATH = ROOT / "02_INPUT/lyrics/lyrics_raw.txt"
ASS_OUTPUT_PATH = ROOT / "02_INPUT/lyrics/lyrics_styled.ass"


def sec_to_ass(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    c = int(round((t - int(t)) * 100))
    if c == 100:
        s += 1
        c = 0
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def sec_to_srt(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def srt_to_sec(value):
    match = re.fullmatch(r"(\d+):(\d{2}):(\d{2})[,\.](\d{3})", value.strip())
    if not match:
        raise ValueError(f"Invalid SRT timestamp: {value}")
    hours, minutes, seconds, milliseconds = match.groups()
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds) / 1000.0
    )


def parse_blocks(text):
    blocks = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if lines:
            blocks.append(lines)
    return blocks


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

    previous_end = -1.0
    for index, cue in enumerate(cues, start=1):
        if cue["start"] < previous_end - 0.01:
            raise ValueError(f"Cue {index} overlaps the previous cue")
        previous_end = cue["end"]

    return cues


def word_count(text):
    return max(len(text.split()), 1)


def wrap_line(line, limit=58):
    if len(line) <= limit:
        return [line]
    if "," in line:
        parts = line.split(",")
        if len(parts) > 1:
            left = parts[0].strip() + ","
            right = ",".join(parts[1:]).strip()
            if right:
                return [left, right]
    words = line.split()
    midpoint = max(1, len(words) // 2)
    return [" ".join(words[:midpoint]), " ".join(words[midpoint:])]


def split_display_segments(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return [""]

    segments = []
    for line in lines:
        segments.extend(wrap_line(line))
    return segments


def allocate_centiseconds(total_cs, parts):
    total_cs = max(total_cs, len(parts))
    base = total_cs // len(parts)
    remainder = total_cs % len(parts)
    return [base + (1 if index < remainder else 0) for index in range(len(parts))]


def karaoke_text(display_text, line_duration, fad_in_ms, fad_out_ms):
    wrapped = split_display_segments(display_text)
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
    return r"{\fad(" + f"{fad_in_ms},{fad_out_ms}" + r")}" + r"\N".join(segments)


def build_header(preset):
    secondary_colour = preset.get("secondary_colour", preset["primary_colour"])
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Lyrics,{preset['font']},{preset['fontsize']},{preset['primary_colour']},{secondary_colour},{preset['outline_colour']},{preset['back_colour']},0,0,0,0,100,100,0,0,{preset['border_style']},{preset['outline']},{preset['shadow']},{preset['alignment']},70,70,{preset['margin_v']},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""


def build_events_from_cues(cues, preset):
    events = []
    for cue in cues:
        display_text = "\n".join(split_display_segments(cue["text"]))
        ass_text = karaoke_text(display_text, cue["end"] - cue["start"], preset['fad_in_ms'], preset['fad_out_ms'])
        events.append(
            f"Dialogue: 0,{sec_to_ass(cue['start'])},{sec_to_ass(cue['end'])},Lyrics,,0,0,0,,{ass_text}"
        )
    return events


ap = argparse.ArgumentParser()
ap.add_argument("--duration", type=float, default=None)
ap.add_argument("--preset", default="spotify_clean")
ap.add_argument("--timing-source", choices=["auto", "srt", "auto-if-missing"], default="auto-if-missing")
args = ap.parse_args()

project = json.loads((ROOT / "01_CONFIG/project_config.json").read_text(encoding="utf-8"))
styles = json.loads((ROOT / "01_CONFIG/lyric_style_presets.json").read_text(encoding="utf-8"))
preset = styles[args.preset]
duration = args.duration or project["song_duration_sec"]
header = build_header(preset)

use_timed_srt = args.timing_source == "srt" or (
    args.timing_source == "auto-if-missing" and TIMED_SRT_PATH.exists() and TIMED_SRT_PATH.read_text(encoding="utf-8-sig").strip()
)

if use_timed_srt:
    cues = load_srt_cues(TIMED_SRT_PATH)
    ASS_OUTPUT_PATH.write_text(header + "\n".join(build_events_from_cues(cues, preset)) + "\n", encoding="utf-8")
    print(f"Lyrics ASS generated from timed SRT: {TIMED_SRT_PATH.relative_to(ROOT)}")
else:
    raw = RAW_LYRICS_PATH.read_text(encoding="utf-8")
    blocks = parse_blocks(raw)
    segment_duration = duration / max(len(blocks), 1)
    events = []
    srt = []
    srt_index = 1

    for block_index, block_lines in enumerate(blocks):
        block_start = block_index * segment_duration + min(0.2, segment_duration * 0.1)
        block_end = (block_index + 1) * segment_duration - min(0.2, segment_duration * 0.1)
        if block_end <= block_start:
            block_end = block_start + 0.6
        block_duration = block_end - block_start
        weights = [word_count(line) for line in block_lines]
        total_weight = sum(weights)
        cursor = block_start

        for line, weight in zip(block_lines, weights):
            line_duration = max(0.6, block_duration * (weight / total_weight))
            line_end = min(block_end, cursor + line_duration)
            if line_end <= cursor:
                line_end = cursor + 0.6

            display_text = "\n".join(split_display_segments(line))
            ass_text = karaoke_text(display_text, line_end - cursor, preset['fad_in_ms'], preset['fad_out_ms'])
            events.append(f"Dialogue: 0,{sec_to_ass(cursor)},{sec_to_ass(line_end)},Lyrics,,0,0,0,,{ass_text}")
            srt += [str(srt_index), f"{sec_to_srt(cursor)} --> {sec_to_srt(line_end)}", display_text, ""]
            srt_index += 1
            cursor = line_end

    ASS_OUTPUT_PATH.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    TIMED_SRT_PATH.write_text("\n".join(srt), encoding="utf-8")
    print("Lyrics ASS/SRT generated from raw lyrics using automatic timing.")
