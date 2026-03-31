from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
project = json.loads((ROOT / "01_CONFIG/project_config.json").read_text(encoding="utf-8"))
styles = json.loads((ROOT / "01_CONFIG/lyric_style_presets.json").read_text(encoding="utf-8"))
style = styles[project.get("title_card_style", "release_title_card")]


def build_card(duration_sec):
	title_font = style.get("font", "Cambria")
	artist_font = style.get("artist_font", "Georgia")
	meta_font = style.get("meta_font", artist_font)
	title_size = style.get("fontsize", 58)
	artist_size = style.get("artist_fontsize", 24)
	meta_size = style.get("meta_fontsize", 18)
	primary = style.get("primary_colour", "&H00EEF7FF")
	accent = style.get("accent_colour", style.get("secondary_colour", primary))
	meta = style.get("meta_colour", accent)
	outline = style.get("outline_colour", "&H00060E1E")
	back = style.get("back_colour", "&H00000000")
	blur = style.get("blur", 1.1)
	fade_in = style.get("fad_in_ms", 260)
	fade_out = style.get("fad_out_ms", 520)
	title_text = project["title"].upper()
	artist_text = project["artist"].upper()
	meta_text = project.get("album_or_series", "").upper()
	end_time = f"0:00:{int(duration_sec):02d}.00"

	return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: TitleArtist,{artist_font},{artist_size},{accent},{accent},{outline},{back},1,0,0,0,100,100,2,0,1,2,1,2,80,80,260,1
Style: TitleMain,{title_font},{title_size},{primary},{primary},{outline},{back},1,0,0,0,100,100,1,0,1,4,1,2,80,80,196,1
Style: TitleMeta,{meta_font},{meta_size},{meta},{meta},{outline},{back},0,0,0,0,100,100,2,0,1,1,1,2,80,80,142,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,{end_time},TitleArtist,,0,0,0,,{{\\fad({fade_in},{fade_out})\\blur{blur}\\pos(640,218)}}{artist_text}
Dialogue: 0,0:00:00.08,{end_time},TitleMain,,0,0,0,,{{\\fad({fade_in + 60},{fade_out + 120})\\blur{blur}\\pos(640,320)}}{title_text}
Dialogue: 0,0:00:00.24,{end_time},TitleMeta,,0,0,0,,{{\\fad({fade_in + 140},{fade_out + 180})\\blur{max(0.6, blur - 0.2)}\\pos(640,406)}}{meta_text}
"""


(ROOT / "03_WORK/overlays/title_intro.ass").write_text(build_card(4), encoding="utf-8")
(ROOT / "03_WORK/overlays/title_outro.ass").write_text(build_card(6), encoding="utf-8")
print("Title cards written.")
