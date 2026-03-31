import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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


def parse_blocks(text):
    blocks = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if lines:
            blocks.append(lines)
    return blocks


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


def allocate_centiseconds(total_cs, parts):
    total_cs = max(total_cs, len(parts))
    base = total_cs // len(parts)
    remainder = total_cs % len(parts)
    return [base + (1 if index < remainder else 0) for index in range(len(parts))]


def karaoke_text(line, line_duration, fad_in_ms, fad_out_ms):
    wrapped = wrap_line(line)
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


ap = argparse.ArgumentParser()
ap.add_argument("--duration", type=float, default=None)
ap.add_argument("--preset", default="spotify_clean")
args = ap.parse_args()

project = json.loads((ROOT / "01_CONFIG/project_config.json").read_text(encoding="utf-8"))
styles = json.loads((ROOT / "01_CONFIG/lyric_style_presets.json").read_text(encoding="utf-8"))
preset = styles[args.preset]
duration = args.duration or project["song_duration_sec"]
raw = (ROOT / "02_INPUT/lyrics/lyrics_raw.txt").read_text(encoding="utf-8")
blocks = parse_blocks(raw)
segment_duration = duration / max(len(blocks), 1)
secondary_colour = preset.get("secondary_colour", preset["primary_colour"])

header = f"""[Script Info]
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

        display_lines = wrap_line(line)
        display_text = "\n".join(display_lines)
        ass_text = karaoke_text(line, line_end - cursor, preset['fad_in_ms'], preset['fad_out_ms'])
        events.append(f"Dialogue: 0,{sec_to_ass(cursor)},{sec_to_ass(line_end)},Lyrics,,0,0,0,,{ass_text}")
        srt += [str(srt_index), f"{sec_to_srt(cursor)} --> {sec_to_srt(line_end)}", display_text, ""]
        srt_index += 1
        cursor = line_end

(ROOT / "02_INPUT/lyrics/lyrics_styled.ass").write_text(header + "\n".join(events) + "\n", encoding="utf-8")
(ROOT / "02_INPUT/lyrics/lyrics_timed.srt").write_text("\n".join(srt), encoding="utf-8")
print("Lyrics ASS/SRT generated.")
