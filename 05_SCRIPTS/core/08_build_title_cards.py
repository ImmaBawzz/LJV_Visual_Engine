from pathlib import Path
import json
ROOT = Path(__file__).resolve().parents[2]
project = json.loads((ROOT/"01_CONFIG/project_config.json").read_text(encoding="utf-8"))
intro=f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Title,Arial,48,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,3,2,0,2,80,80,160,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,0:00:04.00,Title,,0,0,0,,{{\\fad(250,400)}}{project['artist']}\\N{project['title']}
"""
outro=f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Title,Arial,42,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,3,2,0,2,80,80,160,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,0:00:04.00,Title,,0,0,0,,{{\\fad(250,400)}}{project['artist']}\\N{project['title']}
"""
(ROOT/"03_WORK/overlays/title_intro.ass").write_text(intro, encoding="utf-8")
(ROOT/"03_WORK/overlays/title_outro.ass").write_text(outro, encoding="utf-8")
print("Title cards written.")
